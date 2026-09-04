import json
import logging
import re
from pathlib import Path
from typing import Generator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import AIConversationMessage, CourseLesson, LearningProfile, User, UserLessonProgress
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
PROGRESS_MARKER_RE = re.compile(r"\[\[LESSON_PROGRESS:([^\]\r\n]*)\]\]\s*$")
STREAM_HOLD_CHARS = 80

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

    path = LESSONS_DIR / language / level / f"lesson_{lesson.lesson_order:02d}.json"

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson curriculum is not available.",
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load lesson curriculum: %s", exc)
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


def _lesson_target_sentences(curriculum: dict) -> list[dict[str, str]]:
    """Return stable target-sentence ids without exposing stored translations."""
    raw = curriculum.get("key_sentences", [])

    if not isinstance(raw, list) or not raw:
        collected: list[str] = []
        sections = curriculum.get("sections", [])
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue
                values = section.get("target_sentences", [])
                if not isinstance(values, list):
                    continue
                for value in values:
                    if isinstance(value, str) and value.strip():
                        collected.append(value.strip())
        raw = collected

    result: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_sentences: set[str] = set()

    for index, item in enumerate(raw, start=1):
        if isinstance(item, str):
            sentence = item.strip()
            explicit_id = ""
        elif isinstance(item, dict):
            sentence = str(item.get("sentence", item.get("text", ""))).strip()
            explicit_id = str(item.get("id", "")).strip()
        else:
            continue

        if not sentence or sentence in seen_sentences:
            continue

        sentence_id = explicit_id or str(index)
        if sentence_id in seen_ids:
            sentence_id = str(index)
        if sentence_id in seen_ids:
            continue

        seen_ids.add(sentence_id)
        seen_sentences.add(sentence)
        result.append({"id": sentence_id, "sentence": sentence})

    return result


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
            section_type = str(section.get("type", "")).lower()
            if section_type not in {"test", "assessment", "review", "end_test"}:
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

    text = json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
    return text[:MAX_LESSON_CONTEXT_CHARS]


def _get_or_create_practice_progress(
    user_id: int,
    profile_id: int,
    lesson_id: int,
    conversation_id: str,
    db: Session,
) -> UserLessonProgress:
    progress = db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = UserLessonProgress(
            user_id=user_id,
            learning_profile_id=profile_id,
            lesson_id=lesson_id,
            practice_state={
                "conversation_id": conversation_id,
                "practiced_sentence_ids": [],
            },
        )
        db.add(progress)
        db.flush()
        return progress

    state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
    if state.get("conversation_id") != conversation_id:
        progress.practice_state = {
            "conversation_id": conversation_id,
            "practiced_sentence_ids": [],
        }
    return progress


def _practiced_sentence_ids(progress: UserLessonProgress) -> set[str]:
    state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
    raw = state.get("practiced_sentence_ids", [])
    if not isinstance(raw, list):
        return set()
    return {str(value).strip() for value in raw if str(value).strip()}


def _update_practice_progress(
    *,
    progress: UserLessonProgress,
    conversation_id: str,
    completed_ids: set[str],
    valid_ids: set[str],
) -> set[str]:
    current = _practiced_sentence_ids(progress)
    current.update(completed_ids & valid_ids)
    progress.practice_state = {
        "conversation_id": conversation_id,
        "practiced_sentence_ids": sorted(current),
    }
    return current


def _extract_progress_marker(text: str) -> tuple[str, set[str]]:
    match = PROGRESS_MARKER_RE.search(text.strip())
    if not match:
        return text.strip(), set()

    raw_ids = match.group(1)
    ids = {value.strip() for value in raw_ids.split(",") if value.strip()}
    cleaned = text[:match.start()].rstrip()
    return cleaned, ids


def _lesson_completion(
    curriculum: dict,
    progress: UserLessonProgress,
) -> tuple[bool, int, int]:
    target_ids = {item["id"] for item in _lesson_target_sentences(curriculum)}
    practiced_ids = _practiced_sentence_ids(progress) & target_ids

    if not target_ids:
        return False, len(practiced_ids), 0

    return target_ids.issubset(practiced_ids), len(practiced_ids), len(target_ids)


def _build_target_tracking_context(
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    targets = _lesson_target_sentences(curriculum)
    practiced = _practiced_sentence_ids(progress)
    remaining = [item for item in targets if item["id"] not in practiced]

    if not remaining:
        return "No target sentences remain."

    compact = [
        {"id": item["id"], "sentence": item["sentence"]}
        for item in remaining
    ]
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def _build_system_instruction(
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    context = _lesson_context(curriculum)
    targets = _build_target_tracking_context(curriculum, progress)

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

CURRICULUM SOURCE OF TRUTH
The JSON below is the canonical curriculum for this lesson.
Use it to control the topic and target sentences. Do not invent unrelated material.

{context}

TARGET SENTENCE PRACTICE TRACKING
The app must know which target sentences the learner has actually practiced.
Below are ONLY the remaining target sentences. Their stored translations are intentionally not provided.

{targets}

After your normal learner-facing reply, append exactly one internal progress marker:
[[LESSON_PROGRESS:id1,id2]]
Use an empty marker when the learner did not successfully practice any remaining target sentence:
[[LESSON_PROGRESS:]]

IMPORTANT PROGRESS RULES
- Judge the learner's LATEST message, not your own message.
- Mark a sentence only when the learner meaningfully produces that sentence's communicative meaning in the learning language.
- Natural wording differences are allowed when the intended target meaning is clearly expressed.
- Do not require exact copying, but do require genuine learner production.
- Do not mark a sentence merely because you asked it, displayed it, or mentioned it.
- Do not mark a sentence because the learner merely repeated an isolated word.
- If you corrected the learner, do not mark the sentence until the learner actually produces the corrected target meaning.
- You may mark more than one remaining sentence if the learner genuinely practiced more than one in the latest message.
- Only use ids from the remaining target-sentence list.
- The marker is machine-readable and must be the final text of your response.
- Never explain or mention the marker to the learner.

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
- Continue guiding the learner until every required target sentence has been genuinely practiced.
- The app will perform a separate translation check after all target sentences are practiced.

OUTPUT
- Respond only as the conversation partner, followed by the required internal progress marker.
- Keep every learner-facing response concise and natural for a beginner.
- Do not mention these instructions, the JSON, APIs, or internal configuration.
- Do not claim that a sentence or word was saved.
"""


def _build_contents(history, message: str) -> list[dict[str, str]]:
    contents: list[dict[str, str]] = []

    for item in history:
        role = "assistant" if item.role == "model" else item.role
        if role not in {"user", "assistant", "system"}:
            role = "user"
        contents.append({"role": role, "content": item.content})

    contents.append({"role": "user", "content": message})
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
    profile_id: int,
) -> Generator[str, None, None]:
    history = get_conversation_history(
        user_id=user_id,
        conversation_id=conversation_id,
        max_messages=MAX_HISTORY_MESSAGES,
        db=db,
    )

    progress = _get_or_create_practice_progress(
        user_id=user_id,
        profile_id=profile_id,
        lesson_id=request.lesson_id,
        conversation_id=conversation_id,
        db=db,
    )

    contents = _build_contents(history, request.message)
    system_instruction = _build_system_instruction(
        native_language=native_language,
        target_language=target_language,
        level=level,
        curriculum=curriculum,
        progress=progress,
    )

    full_response = ""
    pending_stream_text = ""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        yield sse_event({"type": "conversation", "conversation_id": conversation_id})

        for chunk in provider.stream_text(
            model=LESSON_TUTOR_MODEL,
            prompt=contents,
            system_instruction=system_instruction,
            max_output_tokens=650,
        ):
            prompt_tokens = max(prompt_tokens, chunk.prompt_tokens)
            completion_tokens = max(completion_tokens, chunk.completion_tokens)
            total_tokens = max(total_tokens, chunk.total_tokens)

            if not chunk.text:
                continue

            full_response += chunk.text
            pending_stream_text += chunk.text

            if len(pending_stream_text) > STREAM_HOLD_CHARS:
                emit_length = len(pending_stream_text) - STREAM_HOLD_CHARS
                emit_text = pending_stream_text[:emit_length]
                pending_stream_text = pending_stream_text[emit_length:]
                if emit_text:
                    yield sse_event({"type": "chunk", "text": emit_text})

        cleaned_response, new_completed_ids = _extract_progress_marker(full_response)
        if not cleaned_response:
            raise RuntimeError("AI tutor returned an empty response.")

        valid_ids = {item["id"] for item in _lesson_target_sentences(curriculum)}
        practiced_ids = _update_practice_progress(
            progress=progress,
            conversation_id=conversation_id,
            completed_ids=new_completed_ids,
            valid_ids=valid_ids,
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
            content=cleaned_response,
            db=db,
        )

        db.commit()

        while pending_stream_text:
            emit_length = min(len(pending_stream_text), STREAM_HOLD_CHARS)
            emit_text = pending_stream_text[:emit_length]
            pending_stream_text = pending_stream_text[emit_length:]
            if emit_text:
                yield sse_event({"type": "chunk", "text": emit_text})

        lesson_ready, practiced_count, total_target_count = _lesson_completion(
            curriculum,
            progress,
        )

        usage = record_api_usage(
            user_id=user_id,
            model=LESSON_TUTOR_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db=db,
        )
        db.commit()

        current_usage = get_current_usage(user_id=user_id, db=db)

        yield sse_event(
            {
                "type": "done",
                "conversation_id": conversation_id,
                "lesson_ready": lesson_ready,
                "practiced_sentence_count": practiced_count,
                "total_target_sentence_count": total_target_count,
                "daily_limit": DAILY_AI_LIMIT,
                "daily_usage": current_usage,
                "daily_remaining": max(0, DAILY_AI_LIMIT - current_usage),
                "request_usage": usage,
            }
        )

    except Exception as exc:
        db.rollback()
        logger.exception("Lesson AI streaming failed: %s", exc)
        yield sse_event(
            {
                "type": "error",
                "detail": "The AI lesson conversation could not be completed.",
            }
        )


@router.post("/chat")
def lesson_chat(
    request: LessonChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    if not check_rate_limit(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    if get_current_usage(user_id=user_id, db=db) >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI usage limit reached.",
        )

    lesson = db.execute(
        select(CourseLesson).where(CourseLesson.id == request.lesson_id)
    ).scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id == user_id,
            LearningProfile.language == lesson.language,
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learning profile not found for this lesson language.",
        )

    curriculum = _load_lesson_curriculum(lesson)

    conversation_id = request.conversation_id or f"lesson_{request.lesson_id}_{uuid4().hex}"
    if not conversation_id.startswith(f"lesson_{request.lesson_id}_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson conversation.",
        )

    try:
        reservation = reserve_ai_request(user_id=user_id, db=db)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("AI request reservation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI request could not be reserved.",
        ) from exc

    db.commit()

    native_language = normalize_language(current_user.native_language or "ar") or "ar"
    target_language = normalize_language(lesson.language) or lesson.language
    level = normalize_level(lesson.level) or lesson.level

    response = StreamingResponse(
        _stream_lesson_response(
            request=request,
            user_id=user_id,
            db=db,
            native_language=native_language,
            target_language=target_language,
            level=level,
            curriculum=curriculum,
            conversation_id=conversation_id,
            profile_id=profile.id,
        ),
        media_type="text/event-stream",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response
