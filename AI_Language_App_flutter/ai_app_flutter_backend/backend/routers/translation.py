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

# Translation has a preferred dedicated model, but can fall back to the
# application's main AI model if the dedicated translation models are
# temporarily unavailable. Fallbacks are attempted sequentially, never in
# parallel, so a normal successful request uses only one model.
TRANSLATION_MODEL = (
    os.getenv("OPENROUTER_TRANSLATION_MODEL")
    or "google/gemma-4-31b-it:free"
)

TRANSLATION_FALLBACK_MODEL = (
    os.getenv("OPENROUTER_TRANSLATION_FALLBACK_MODEL")
    or "google/gemma-4-26b-a4b-it:free"
)

# Reuse the same main model already configured for the rest of the AI system.
# This avoids introducing a fourth model just for translation fallback.
TRANSLATION_MAIN_MODEL = os.getenv("OPENROUTER_MAIN_MODEL") or "minimax/minimax-m2.7:free"

# MiniMax M2.7 is a reasoning-capable model. A small 256-token ceiling can be
# consumed by its internal reasoning before it reaches the final translation,
# which causes OpenRouter to return finish_reason="length" with no final text.
# Keep enough output budget for both reasoning and the actual translation.
TRANSLATION_MAX_OUTPUT_TOKENS = 2048

_TRANSLATION_FALLBACK_STATUS_CODES = {
    402,
    404,
    408,
    409,
    429,
    500,
    502,
    503,
    504,
}


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


def _should_try_fallback(exc: Exception) -> bool:
    if isinstance(exc, OpenRouterRequestError):
        return exc.status_code in _TRANSLATION_FALLBACK_STATUS_CODES
    return isinstance(exc, RuntimeError)


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

        # Keep the three attempts sequential. The next model is called only
        # when the previous one fails with a retryable error.
        models_to_try = []
        for model in (
            TRANSLATION_MODEL,
            TRANSLATION_FALLBACK_MODEL,
            TRANSLATION_MAIN_MODEL,
        ):
            if model and model not in models_to_try:
                models_to_try.append(model)

        for index, model in enumerate(models_to_try):
            try:
                response, translation = _generate_translation(
                    model=model,
                    text=text,
                    source_language=source_language,
                    target_language=target_language,
                )
                break
            except Exception as exc:
                last_error = exc

                if index >= len(models_to_try) - 1 or not _should_try_fallback(exc):
                    raise

                next_model = models_to_try[index + 1]
                logger.warning(
                    "Translation model failed (%s); trying next model=%s "
                    "for user_id=%s",
                    exc,
                    next_model,
                    current_user.id,
                )

        if response is None or translation is None:
            raise RuntimeError("All configured translation models failed.") from last_error

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
