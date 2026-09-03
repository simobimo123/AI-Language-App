import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.ai.normalization import normalize_language
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request


router = APIRouter(
    prefix="/ai/translation",
    tags=["AI Translation"],
)

logger = logging.getLogger(__name__)
TRANSLATION_MODEL = os.getenv("OPENROUTER_TRANSLATION_MODEL") or os.getenv("OPENROUTER_MAIN_MODEL")
if not TRANSLATION_MODEL:
    raise RuntimeError(
        "OPENROUTER_TRANSLATION_MODEL or OPENROUTER_MAIN_MODEL must be configured in the .env file"
    )

TRANSLATION_MAX_OUTPUT_TOKENS = 1200


class TranslationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _translation_prompt(text: str, source_language: str, target_language: str) -> str:
    return f"""
You are a translation engine for a language-learning app.

Translate the text below accurately from {source_language} to {target_language}.

STRICT RULES:
- Return ONLY the translated text.
- Do not explain anything.
- Do not answer the message.
- Do not add labels such as Translation:.
- Do not add quotation marks, emojis, or notes.
- Preserve the meaning, tone, punctuation, names, numbers, and sentence breaks.
- Keep the translation concise. Do not repeat the source text.
- The final response must contain the translation itself, even for a very short input.

TEXT TO TRANSLATE:
{text}
""".strip()


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
        response = provider.generate_text(
            model=TRANSLATION_MODEL,
            prompt=_translation_prompt(
                text=text,
                source_language=source_language,
                target_language=target_language,
            ),
            max_output_tokens=TRANSLATION_MAX_OUTPUT_TOKENS,
        )

        translation = response.text.strip()
        if not translation:
            raise RuntimeError("Translation model returned an empty response.")

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
