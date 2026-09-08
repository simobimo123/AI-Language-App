import logging

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
HINT_MAX_OUTPUT_TOKENS = 300


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
        f"Reply to this tutor message in {target_language}. "
        "Give one short natural learner reply. "
        f"Translate that reply to {native_language}. "
        "Return exactly:\n"
        "SUGGESTION: <reply>\n"
        "TRANSLATION: <translation>\n\n"
        f"Tutor message: {tutor_message}"
    )


def _parse_hint(text: str) -> tuple[str, str]:
    suggestion = ""
    translation = ""

    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("SUGGESTION:"):
            suggestion = stripped.split(":", 1)[1].strip()
        elif upper.startswith("TRANSLATION:"):
            translation = stripped.split(":", 1)[1].strip()

    if not suggestion or not translation:
        raise RuntimeError("AI hint returned an invalid format.")

    return suggestion, translation


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
