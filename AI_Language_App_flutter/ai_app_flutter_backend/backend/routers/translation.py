import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.ai.client import OpenRouterRequestError
from services.ai.normalization import normalize_language
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request


router = APIRouter(
    prefix="/ai/translation",
    tags=["AI Translation"],
)

logger = logging.getLogger(__name__)

# Translation uses its own model so the main AI teacher model is not affected.
# The environment variable remains the preferred configuration, while the
# free Gemma model is the safe default for this short, direct task.
TRANSLATION_MODEL = (
    os.getenv("OPENROUTER_TRANSLATION_MODEL")
    or "google/gemma-4-31b-it:free"
)

# If the primary translation model is unavailable or temporarily rate-limited,
# retry the same request with a separate free model. This fallback is used only
# by the translation endpoint and never changes the main AI teacher model.
TRANSLATION_FALLBACK_MODEL = (
    os.getenv("OPENROUTER_TRANSLATION_FALLBACK_MODEL")
    or "meta-llama/llama-3.1-8b-instruct:free"
)

# Translation should be a short-answer operation. Keep the completion budget
# small so a one-sentence translation does not reserve an unnecessarily large
# output budget.
TRANSLATION_MAX_OUTPUT_TOKENS = 256

# These failures can reasonably be recovered by trying the configured fallback
# model. Client/authentication errors such as 400/401/403 are not retried.
_TRANSLATION_FALLBACK_STATUS_CODES = {
    402,  # provider/model requires unavailable credits
    404,  # model/provider route unavailable
    408,  # request timeout
    409,  # transient provider conflict
    429,  # rate limit / quota
    500,
    502,
    503,
    504,
}


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _translation_prompt(text: str, source_language: str, target_language: str) -> str:
    """Build the smallest useful prompt for a direct translation request."""
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
    """Generate one translation without changing request/quota accounting."""
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
        try:
            response, translation = _generate_translation(
                model=TRANSLATION_MODEL,
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
        except OpenRouterRequestError as exc:
            if exc.status_code not in _TRANSLATION_FALLBACK_STATUS_CODES:
                raise

            logger.warning(
                "Primary translation model failed with HTTP %s; "
                "trying fallback model=%s for user_id=%s",
                exc.status_code,
                TRANSLATION_FALLBACK_MODEL,
                current_user.id,
            )

            response, translation = _generate_translation(
                model=TRANSLATION_FALLBACK_MODEL,
                text=text,
                source_language=source_language,
                target_language=target_language,
            )
        except RuntimeError as exc:
            # Network errors and empty model responses do not expose an HTTP
            # status code, so give the translation fallback a chance as well.
            logger.warning(
                "Primary translation model failed (%s); trying fallback "
                "model=%s for user_id=%s",
                exc,
                TRANSLATION_FALLBACK_MODEL,
                current_user.id,
            )

            response, translation = _generate_translation(
                model=TRANSLATION_FALLBACK_MODEL,
                text=text,
                source_language=source_language,
                target_language=target_language,
            )

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
            "AI translation failed for user_id=%s: %s",
            current_user.id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation is temporarily unavailable.",
        ) from exc
