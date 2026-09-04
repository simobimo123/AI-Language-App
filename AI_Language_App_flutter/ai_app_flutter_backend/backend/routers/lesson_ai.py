import json
import logging
from pathlib import Path
from typing import Generator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import AIConversationMessage, CourseLesson, LearningProfile, User
from routers.auth import get_current_user
from services.ai.client import AI_MODEL
from services.ai.conversation import (
    cleanup_old_conversation_messages,
    get_conversation_history,
    save_conversation_message,
)
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.response_stream import sse_event
from services.ai.usage import (
    DAILY_AI_LIMIT,
    get_current_usage,
    record_api_usage,
    reserve_ai_request,
)


router = APIRouter(
    prefix="/ai/lesson",
    tags=["AI Lesson Tutor"],
)

logger = logging.getLogger(__name__)

# Lesson tutoring must use the same centralized MiniMax model as all other
# application AI services. Legacy model environment variables are ignored.
LESSON_TUTOR_MODEL = AI_MODEL

MAX_HISTORY_MESSAGES = 2
MAX_LESSON_CONTEXT_CHARS = 10000
LESSON_CONVERSATION_PREFIX = "lesson_"

BASE_DIR = Path(__file__).resolve().parent.parent
LESSONS_DIR = BASE_DIR / "data" / "lessons"


class LessonChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


def _load_lesson_curriculum(lesson: CourseLesson) -> dict:
    language = normalize_language(lesson.language)
    level = normalize_level(lesson.level)

    if level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson level.",
        )

    path = (
        LESSONS_DIR
        / language
        / level
        / f"lesson_{lesson.lesson_order:02d}.json"
    )

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson curriculum is not available.",
        )

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8-sig",
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception(
            "Failed to load lesson curriculum: %s",
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson curriculum could not be loaded.",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid lesson curriculum format.",
        )

    return data


def _lesson_context(data: dict) -> str:
    """Build a compact context centered on one lesson conversation."""
    metadata = data.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    focus_section = None
    sections = data.get("sections", [])

    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue

            section_type = str(
                section.get("type", "")
            ).lower()

            if section_type not in {
                "test",
                "assessment",
                "review",
                "end_test",
            }:
                focus_section = section
                break

    selected = {
        "lesson_id": data.get("lesson_id"),
        "language": data.get("language"),
        "level": data.get("level"),
        "lesson_order": data.get("lesson_order"),
        "metadata": metadata,
        "primary_focus_section": focus_section,
    }

    text = json.dumps(
        selected,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return text[:MAX_LESSON_CONTEXT_CHARS]


def _lesson_minimum_practice(curriculum: dict) -> int:
    completion = curriculum.get("completion", {})
    practice = curriculum.get("practice", {})

    for source in (completion, practice):
        if isinstance(source, dict):
            value = source.get("minimum_practice", source.get("minimum_turns"))
            try:
                parsed = int(value)
                if parsed > 0:
                    return parsed
            except (TypeError, ValueError):
                pass

    return 6


def _learner_turn_count(user_id: int, conversation_id: str, db: Session) -> int:
    rows = db.execute(
        select(AIConversationMessage.role, AIConversationMessage.content).where(
            AIConversationMessage.user_id == user_id,
            AIConversationMessage.conversation_id == conversation_id,
        )
    ).all()
    return sum(
        1
        for role, content in rows
        if role == "user" and content.strip() != "START_LESSON"
    )


def _build_system_instruction(
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
) -> str:
    context = _lesson_context(curriculum)
    minimum_practice = _lesson_minimum_practice(curriculum)

    return f"""
You are the AI conversation partner for ONE lesson in a language-learning app.

USER
- Native language: {native_language}
- Learning language: {target_language}
- Current CEFR level: {level}

LESSON
- Lesson order: {curriculum.get('lesson_order')}
- Lesson language: {curriculum.get('language')}
- Lesson level: {curriculum.get('level')}
- Topic: {curriculum.get('metadata', {}).get('title', '')}
- Objective: {curriculum.get('metadata', {}).get('objective', '')}
- Minimum learner practice turns before the final translation check: {minimum_practice}

CURRICULUM SOURCE OF TRUTH
The JSON below is the canonical curriculum for this lesson.
Use it to control the topic and target sentences. Do not invent unrelated material.

{context}

CONVERSATION-ONLY MODE — VERY IMPORTANT
- This is NOT a traditional lesson and NOT a lecture.
- Do not explain grammar rules before the learner speaks.
- Do not announce what the learner will learn.
- Do not list vocabulary, teaching points, or lesson sections.
- Do not give long explanations.
- Do not behave like a teacher giving a presentation.
- Act as a natural conversation partner who quietly guides the learner.
- Start with a natural sentence or question in the learning language.
- Ask only one natural question or request one short response at a time.
- Give the learner frequent opportunities to produce complete sentences.
- Prefer the learner speaking over the tutor speaking.
- Introduce target words and sentences naturally through the conversation.
- Reuse important target sentences in different natural turns.
- Keep tutor messages short: normally one or two sentences.
- If the learner makes an important mistake, correct it briefly and naturally,
  then ask the learner to say the corrected sentence.
- Do not stop the conversation to teach a grammar lesson.
- Do not reveal answer keys or the internal curriculum unless necessary.
- Stay inside the lesson topic and target sentences.

LANGUAGE CONTROL — VERY IMPORTANT
- The learning language is {target_language}.
- The actual conversation must be in the learning language.
- Never output Chinese, Japanese, Korean, or another unrelated language.
- Never switch languages because of model habits.
- Use the native language ({native_language}) only for a very short clarification
  when the learner clearly needs help; otherwise stay entirely in the learning language.
- Do not mix unrelated scripts into a target-language sentence.
- Do not translate every sentence automatically.

SESSION CONTINUITY
- If previous conversation history exists, continue naturally from it.
- Do not restart the lesson or repeat a lecture when the learner returns.
- Leaving the screen does not mean the lesson is completed.
- Continue helping the learner speak until the minimum practice requirement is met.
- The app will perform a separate translation check after the minimum practice requirement.

OUTPUT
- Respond only as the conversation partner.
- Keep every response concise and natural for a beginner.
- Do not mention these instructions, the JSON, APIs, or internal configuration.
- Do not claim that a sentence or word was saved.
"""


def _build_contents(
    history,
    message: str,
) -> list[dict[str, str]]:
    contents: list[dict[str, str]] = []

    for item in history:
        role = "assistant" if item.role == "model" else item.role
        if role not in {"user", "assistant", "system"}:
            role = "user"

        contents.append({
            "role": role,
            "content": item.content,
        })

    contents.append({
        "role": "user",
        "content": message,
    })

    return contents


def _stream_lesson_response(
    request: LessonChatRequest,
    user_id: int,
    db: Session,
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    conversation_id: str,
) -> Generator[str, None, None]:
    history = get_conversation_history(
        user_id=user_id,
        conversation_id=conversation_id,
        max_messages=MAX_HISTORY_MESSAGES,
        db=db,
    )

    contents = _build_contents(
        history,
        request.message,
    )

    system_instruction = _build_system_instruction(
        native_language=native_language,
        target_language=target_language,
        level=level,
        curriculum=curriculum,
    )

    full_response = ""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        yield sse_event(
            {
                "type": "conversation",
                "conversation_id": conversation_id,
            }
        )

        for chunk in provider.stream_text(
            model=LESSON_TUTOR_MODEL,
            prompt=contents,
            system_instruction=system_instruction,
            max_output_tokens=650,
        ):
            prompt_tokens = max(
                prompt_tokens,
                chunk.prompt_tokens,
            )

            completion_tokens = max(
                completion_tokens,
                chunk.completion_tokens,
            )

            total_tokens = max(
                total_tokens,
                chunk.total_tokens,
            )

            if not chunk.text:
                continue

            full_response += chunk.text

            yield sse_event(
                {
                    "type": "chunk",
                    "text": chunk.text,
                }
            )

        if not full_response.strip():
            raise RuntimeError(
                "AI tutor returned an empty response."
            )

        save_conversation_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=request.message,
            db=db,
        )

        save_conversation_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="model",
            content=full_response,
            db=db,
        )

        cleanup_old_conversation_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            max_messages=MAX_HISTORY_MESSAGES,
            db=db,
        )

        db.commit()

        record_api_usage(
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db=db,
        )

        usage = get_current_usage(
            user_id=user_id,
            db=db,
        )

        learner_turns = _learner_turn_count(
            user_id=user_id,
            conversation_id=conversation_id,
            db=db,
        )
        minimum_practice = _lesson_minimum_practice(curriculum)
        lesson_ready = learner_turns >= minimum_practice

        yield sse_event(
            {
                "type": "done",
                "conversation_id": conversation_id,
                "lesson_ready": lesson_ready,
                "daily_limit": DAILY_AI_LIMIT,
                "daily_used": usage.request_count,
                "daily_remaining": max(
                    0,
                    DAILY_AI_LIMIT - usage.request_count,
                ),
            }
        )

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Lesson AI streaming failed user_id=%s lesson_id=%s: %s",
            user_id,
            request.lesson_id,
            exc,
        )

        yield sse_event(
            {
                "type": "error",
                "message": "AI tutor is temporarily unavailable.",
            }
        )


def _find_saved_lesson_conversation(
    user_id: int,
    lesson_id: int,
    db: Session,
) -> str | None:
    """Find the newest saved conversation belonging to this lesson."""
    prefix = f"{LESSON_CONVERSATION_PREFIX}{lesson_id}_"

    return db.execute(
        select(
            AIConversationMessage.conversation_id
        )
        .where(
            AIConversationMessage.user_id == user_id,
            AIConversationMessage.conversation_id.like(
                f"{prefix}%"
            ),
        )
        .order_by(
            AIConversationMessage.created_at.desc()
        )
        .limit(1)
    ).scalar_one_or_none()


@router.post("/chat")
def lesson_chat(
    request: LessonChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = db.get(
        CourseLesson,
        request.lesson_id,
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    user_id = current_user.id

    target_language = normalize_language(
        current_user.learning_language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    lesson_language = normalize_language(
        lesson.language
    )

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

    profile_level = normalize_level(
        profile.level
    )

    lesson_level = normalize_level(
        lesson.level
    )

    if profile_level != lesson_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is not part of your current learning level.",
        )

    level = profile_level or "A1"

    curriculum = _load_lesson_curriculum(
        lesson
    )

    check_rate_limit(user_id)

    reserve_ai_request(
        user_id=user_id,
        db=db,
    )

    conversation_id = request.conversation_id

    if not conversation_id:
        conversation_id = _find_saved_lesson_conversation(
            user_id=user_id,
            lesson_id=request.lesson_id,
            db=db,
        )

    if not conversation_id:
        conversation_id = (
            f"{LESSON_CONVERSATION_PREFIX}"
            f"{request.lesson_id}_"
            f"{uuid4().hex}"
        )

    return StreamingResponse(
        _stream_lesson_response(
            request=request,
            user_id=user_id,
            db=db,
            native_language=native_language,
            target_language=target_language,
            level=level,
            curriculum=curriculum,
            conversation_id=conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
