import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LearningProfile, User
from routers.auth import get_current_user
from services.ai.conversation import get_conversation_history
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request

from routers.lesson_ai import (
    MAX_HISTORY_MESSAGES,
    _find_saved_lesson_conversation,
    _lesson_context,
    _load_lesson_curriculum,
)

router = APIRouter(
    prefix="/ai/lesson",
    tags=["AI Lesson Tutor"],
)

logger = logging.getLogger(__name__)

HINT_MODEL = os.getenv("OPENROUTER_MAIN_MODEL")
if not HINT_MODEL:
    raise RuntimeError("OPENROUTER_MAIN_MODEL is not configured in the .env file")


class LessonHintRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


def _hint_prompt(
    *,
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    history,
) -> str:
    history_text = json.dumps(
        [
            {
                "role": item.role,
                "content": item.content,
            }
            for item in history
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"""
You are helping a learner answer the CURRENT turn of a language-learning conversation.

Native language: {native_language}
Learning language: {target_language}
CEFR level: {level}

The canonical lesson context is:
{_lesson_context(curriculum)}

Recent conversation history:
{history_text}

TASK
Generate ONE short, natural suggested answer that the learner could independently say or type NOW.
The suggestion must directly answer the latest tutor question/request and stay within the lesson topic.
Prefer a sentence using the lesson's target vocabulary or key sentence patterns when appropriate.
Make it suitable for the learner's CEFR level.
Do not give multiple choices.
Do not explain grammar.
Do not add commentary.

OUTPUT FORMAT — EXACTLY TWO LINES
SUGGESTION: <one sentence in {target_language}>
TRANSLATION: <the meaning of that sentence in {native_language}>

IMPORTANT
- The suggestion is only a hint. It must NOT be treated as the learner's answer.
- Do not say that you sent, saved, or submitted it.
- Never output unrelated languages.
"""


def _parse_hint(text: str) -> tuple[str, str]:
    suggestion = ""
    translation = ""

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("SUGGESTION:"):
            suggestion = stripped.split(":", 1)[1].strip()
        elif stripped.upper().startswith("TRANSLATION:"):
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
    lesson = db.get(CourseLesson, request.lesson_id)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    user_id = current_user.id
    target_language = normalize_language(current_user.learning_language)
    native_language = normalize_language(current_user.native_language)
    lesson_language = normalize_language(lesson.language)

    if lesson_language != target_language:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson does not belong to your learning language.",
        )

    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id == user_id,
            LearningProfile.language == target_language,
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is not part of your current learning level.",
        )

    profile_level = normalize_level(profile.level)
    lesson_level = normalize_level(lesson.level)

    if profile_level != lesson_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is not part of your current learning level.",
        )

    level = profile_level or "A1"
    curriculum = _load_lesson_curriculum(lesson)

    check_rate_limit(user_id)
    reserve_ai_request(user_id=user_id, db=db)

    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = _find_saved_lesson_conversation(
            user_id=user_id,
            lesson_id=request.lesson_id,
            db=db,
        )

    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start the lesson conversation before requesting a hint.",
        )

    history = get_conversation_history(
        user_id=user_id,
        conversation_id=conversation_id,
        max_messages=MAX_HISTORY_MESSAGES,
        db=db,
    )

    if not history:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is no active lesson conversation for this hint.",
        )

    try:
        response = provider.generate_text(
            model=HINT_MODEL,
            prompt=_hint_prompt(
                native_language=native_language,
                target_language=target_language,
                level=level,
                curriculum=curriculum,
                history=history,
            ),
            max_output_tokens=180,
        )

        suggestion, translation = _parse_hint(response.text)

        record_api_usage(
            user_id=user_id,
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
            user_id,
            request.lesson_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI hint is temporarily unavailable.",
        ) from exc
