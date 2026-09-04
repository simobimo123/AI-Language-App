import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.ai.client import AI_MODEL, OpenRouterRequestError
from services.ai.normalization import normalize_language
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request


router = APIRouter(
    prefix="/ai/translation",
    tags=["AI Translation"],
)

logger = logging.getLogger(__name__)

# Translation uses the exact same centralized MiniMax model as chat,
# classification, vocabulary enrichment, lesson tutoring, hints, and lesson
# generation. No Google/Gemma translation fallback is allowed.
TRANSLATION_MODEL = AI_MODEL
TRANSLATION_MAX_OUTPUT_TOKENS = 2048

# A temporary upstream failure can be retried on the SAME MiniMax model.
# We never switch to another provider/model.
_TRANSLATION_RETRY_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}
TRANSLATION_MAX_RETRIES = 2


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _translation_prompt(text: str, source_language: str, target_language: str) -> str:
    return (
        f"Translate from {source_language} to {target_language}. "
        "Return only the translation, with no explanation or extra text.\n\n"
        f"{text}"
    )


def _generate_translation(
    *,
    model: str,
    text: str,
    source_language: str,
    target_language: str,
):
    response = provider.generate_text(
        model=model,
        prompt=_translation_prompt(
            text=text,
            source_language=source_language,
            target_language=target_language,
        ),
        max_output_tokens=TRANSLATION_MAX_OUTPUT_TOKENS,
    )

    translation = response.text.strip()
    if not translation:
        raise RuntimeError(
            f"Translation model returned an empty response (model={model!r})."
        )

    return response, translation


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, OpenRouterRequestError):
        return exc.status_code in _TRANSLATION_RETRY_STATUS_CODES
    return False


@router.post("/")
def translate_text(
    request: TranslationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text cannot be empty.",
        )

    source_language = normalize_language(current_user.learning_language)
    target_language = normalize_language(current_user.native_language)

    if source_language == target_language:
        return {
            "translation": text,
            "source_language": source_language,
            "target_language": target_language,
        }

    check_rate_limit(current_user.id)
    reserve_ai_request(user_id=current_user.id, db=db)

    try:
        response = None
        translation = None
        last_error = None

        # Retry only the same MiniMax model. This prevents the previous
        # Google/Gemma fallback chain from ever being used again.
        for attempt in range(TRANSLATION_MAX_RETRIES + 1):
            try:
                response, translation = _generate_translation(
                    model=TRANSLATION_MODEL,
                    text=text,
                    source_language=source_language,
                    target_language=target_language,
                )
                break
            except Exception as exc:
                last_error = exc

                if attempt >= TRANSLATION_MAX_RETRIES or not _should_retry(exc):
                    raise

                logger.warning(
                    "MiniMax translation attempt failed (%s); retry=%s/%s "
                    "for user_id=%s",
                    exc,
                    attempt + 1,
                    TRANSLATION_MAX_RETRIES,
                    current_user.id,
                )

        if response is None or translation is None:
            raise RuntimeError(
                "MiniMax translation failed after all retry attempts."
            ) from last_error

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            db=db,
        )
        db.commit()

        return {
            "translation": translation,
            "source_language": source_language,
            "target_language": target_language,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "AI translation failed for user_id=%s model=%s: %s",
            current_user.id,
            TRANSLATION_MODEL,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation is temporarily unavailable.",
        ) from exc
