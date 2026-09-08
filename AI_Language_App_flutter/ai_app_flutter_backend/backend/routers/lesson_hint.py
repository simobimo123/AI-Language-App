import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.ai.client import AI_MODEL
from services.ai.conversation import get_conversation_history
from services.ai.normalization import normalize_language
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request

router = APIRouter(
    prefix="/ai/lesson",
    tags=["AI Lesson Tutor"],
)

logger = logging.getLogger(__name__)

HINT_MODEL = AI_MODEL

# The model may spend part of the output budget on internal reasoning.
# Keep reasoning enabled, but leave enough room for the tiny final answer.
HINT_MAX_OUTPUT_TOKENS = 700


class LessonHintRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    conversation_id: str = Field(min_length=1, max_length=100)


def _latest_tutor_message(history) -> str:
    for item in reversed(history):
        if item.role == "assistant":
            text = str(item.content or "").strip()
            if text:
                return text[:600]
    return ""


def _hint_prompt(
    *,
    tutor_message: str,
    target_language: str,
    native_language: str,
) -> str:
    return (
        f"Give a short learner reply to the tutor in {target_language}. "
        f"Then translate the reply to {native_language}. "
        "Keep both very short. Do not explain. "
        "Your final answer must contain only these two lines:\n"
        "SUGGESTION: <reply>\n"
        "TRANSLATION: <translation>\n\n"
        f"Tutor: {tutor_message}"
    )


def _clean_value(value: str) -> str:
    value = value.strip().strip("`*_ ")
    value = re.sub(r"^[-*•]\s*", "", value)
    return value.strip()


def _parse_hint(text: str) -> tuple[str, str]:
    """Parse the compact final answer without requiring exact line formatting."""
    cleaned = text.strip()

    suggestion_match = re.search(
        r"(?:SUGGESTION|REPLY)\s*:\s*(.+?)(?=\n\s*(?:TRANSLATION|TRANSLATE)\s*:|$)",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    translation_match = re.search(
        r"(?:TRANSLATION|TRANSLATE)\s*:\s*(.+)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if suggestion_match and translation_match:
        suggestion = _clean_value(suggestion_match.group(1))
        translation = _clean_value(translation_match.group(1))
        if suggestion and translation:
            return suggestion, translation

    # Some models return a tiny JSON object despite the plain-text instruction.
    try:
        import json

        data = json.loads(cleaned.strip("` "))
        if isinstance(data, dict):
            suggestion = _clean_value(str(data.get("suggestion", "")))
            translation = _clean_value(str(data.get("translation", "")))
            if suggestion and translation:
                return suggestion, translation
    except Exception:
        pass

    raise RuntimeError("AI hint returned an invalid format.")


@router.post("/hint")
def lesson_hint(
    request: LessonHintRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_language = normalize_language(current_user.learning_language)
    native_language = normalize_language(current_user.native_language)

    # Only the latest tutor message is needed. The lesson JSON, full history,
    # previous learner turns, and lesson metadata are deliberately excluded.
    history = get_conversation_history(
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        max_messages=2,
        db=db,
    )
    tutor_message = _latest_tutor_message(history)

    if not tutor_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is no tutor message to answer.",
        )

    check_rate_limit(current_user.id)
    reserve_ai_request(user_id=current_user.id, db=db)

    try:
        response = provider.generate_text(
            model=HINT_MODEL,
            prompt=_hint_prompt(
                tutor_message=tutor_message,
                target_language=target_language,
                native_language=native_language,
            ),
            max_output_tokens=HINT_MAX_OUTPUT_TOKENS,
        )

        suggestion, translation = _parse_hint(response.text)

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            db=db,
        )
        db.commit()

        return {
            "suggestion": suggestion,
            "translation": translation,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Lesson AI hint failed user_id=%s lesson_id=%s: %s",
            current_user.id,
            request.lesson_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI hint is temporarily unavailable.",
        ) from exc
