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
from models import CourseLesson, LearningProfile, User, UserLessonProgress
from routers.auth import get_current_user
from services.ai.client import AI_MODEL
from services.ai.conversation import get_conversation_history, save_conversation_message
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.response_stream import sse_event
from services.ai.usage import DAILY_AI_LIMIT, get_current_usage, record_api_usage, reserve_ai_request

router = APIRouter(prefix="/ai/lesson", tags=["AI Lesson Tutor"])
logger = logging.getLogger(__name__)

LESSON_TUTOR_MODEL = AI_MODEL
MAX_HISTORY_MESSAGES = 20
MAX_LESSON_CONTEXT_CHARS = 2500
MAX_OUTPUT_TOKENS = 800
PROGRESS_MARKER = "[[LESSON_PROGRESS:"
PROGRESS_MARKER_RE = re.compile(r"\[\[LESSON_PROGRESS:([^\]\r\n]*)\]\]")
STREAM_HOLD_CHARS = 64

BASE_DIR = Path(__file__).resolve().parent.parent
LESSONS_DIR = BASE_DIR / "data" / "lessons"


class LessonChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


def _load_lesson_curriculum(lesson: CourseLesson) -> dict:
    language = normalize_language(lesson.language)
    level = normalize_level(lesson.level)
    if level is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid lesson level.")
    path = LESSONS_DIR / language / level / f"lesson_{lesson.lesson_order:02d}.json"
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson curriculum is not available.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load lesson curriculum: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lesson curriculum could not be loaded.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid lesson curriculum format.")
    return data


def _lesson_target_sentences(curriculum: dict) -> list[dict[str, str]]:
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
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    section_context: dict[str, object] = {}
    sections = data.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_type = str(section.get("type", "")).lower()
            if section_type in {"test", "assessment", "review", "end_test"}:
                continue
            section_context = {
                "title": str(section.get("title", "")).strip(),
                "objective": str(section.get("objective", "")).strip(),
                "scenario": str(section.get("scenario", "")).strip(),
                "focus": section.get("focus", []),
            }
            break
    selected = {
        "topic": str(metadata.get("title", "")).strip(),
        "objective": str(metadata.get("objective", "")).strip(),
        "focus": section_context,
    }
    text = json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
    return text[:MAX_LESSON_CONTEXT_CHARS]


def _get_or_create_practice_progress(user_id: int, profile_id: int, lesson_id: int, conversation_id: str, db: Session) -> UserLessonProgress:
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
            practice_state={"conversation_id": conversation_id, "practiced_sentence_ids": []},
        )
        db.add(progress)
        db.flush()
        return progress
    state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
    if state.get("conversation_id") != conversation_id:
        progress.practice_state = {"conversation_id": conversation_id, "practiced_sentence_ids": []}
    return progress


def _practiced_sentence_ids(progress: UserLessonProgress) -> set[str]:
    state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
    raw = state.get("practiced_sentence_ids", [])
    if not isinstance(raw, list):
        return set()
    return {str(value).strip() for value in raw if str(value).strip()}


def _update_practice_progress(*, progress: UserLessonProgress, conversation_id: str, completed_ids: set[str], valid_ids: set[str]) -> set[str]:
    current = _practiced_sentence_ids(progress)
    current.update(completed_ids & valid_ids)
    progress.practice_state = {"conversation_id": conversation_id, "practiced_sentence_ids": sorted(current)}
    return current


def _extract_progress_marker(text: str) -> tuple[str, set[str]]:
    matches = list(PROGRESS_MARKER_RE.finditer(text))
    if not matches:
        return text.strip(), set()
    match = matches[-1]
    raw_ids = match.group(1)
    ids = {value.strip() for value in raw_ids.split(",") if value.strip()}
    cleaned = PROGRESS_MARKER_RE.sub("", text).strip()
    return cleaned, ids


def _remove_exact_duplicate_response(text: str) -> str:
    """Remove model duplication while preserving legitimate repeated wording."""
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text).strip()
    if not cleaned:
        return cleaned
    match = re.fullmatch(r"(.+?)\s+\1", cleaned, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    normalized = re.sub(r"\s+", " ", cleaned).strip()
    if len(normalized) >= 4 and len(normalized) % 2 == 0:
        half = len(normalized) // 2
        if normalized[:half].rstrip() == normalized[half:].lstrip():
            return normalized[:half].strip()
    sentence_match = re.fullmatch(r"(.+?[.!?。！？])\s+\1", cleaned, flags=re.DOTALL)
    if sentence_match:
        return sentence_match.group(1).strip()
    return cleaned


def _lesson_completion(curriculum: dict, progress: UserLessonProgress) -> tuple[bool, int, int]:
    target_ids = {item["id"] for item in _lesson_target_sentences(curriculum)}
    practiced_ids = _practiced_sentence_ids(progress) & target_ids
    if not target_ids:
        return False, len(practiced_ids), 0
    return target_ids.issubset(practiced_ids), len(practiced_ids), len(target_ids)


def _build_target_tracking_context(curriculum: dict, progress: UserLessonProgress) -> str:
    targets = _lesson_target_sentences(curriculum)
    practiced = _practiced_sentence_ids(progress)
    remaining = [item for item in targets if item["id"] not in practiced]
    if not remaining:
        return "[]"
    compact = [{"id": item["id"], "sentence": item["sentence"]} for item in remaining]
    return json.dumps(compact, ensure_ascii=False, separators=(",", ":"))


def _build_system_instruction(native_language: str, target_language: str, level: str, curriculum: dict, progress: UserLessonProgress) -> str:
    context = _lesson_context(curriculum)
    targets = _build_target_tracking_context(curriculum, progress)
    teacher_instructions = curriculum.get("teacher_instructions", {})
    if not isinstance(teacher_instructions, dict):
        teacher_instructions = {}
    start_message = str(teacher_instructions.get("start_message", "")).strip()
    start_rule = ""
    if start_message:
        start_rule = f"""
START_LESSON
When the latest user message is START_LESSON, begin the lesson with exactly one short opening reply. Base the opening on this curriculum start message:
{start_message}
Do not output the opening twice, do not echo START_LESSON, and do not add a second greeting or question after the opening."""
    return f"""You are the AI conversation partner for one language-learning lesson.

Language: {target_language}
Learner native language: {native_language}
CEFR level: {level}

LESSON CONTEXT
{context}

REMAINING TARGET SENTENCES
{targets}

Use only the lesson context above. Guide the learner through a natural conversation and keep the topic focused. Do not lecture, list vocabulary, explain grammar at length, or reveal internal curriculum data. Ask only one short question/request at a time and give the learner most of the speaking turns. Keep replies to one or two short sentences. Use the learning language; use the native language only for a very brief clarification when clearly necessary. If the learner makes an important mistake, correct it briefly and ask them to produce the corrected sentence.

CONTINUITY
Use the full conversation history provided separately. Continue naturally from it; never restart or ask for information already established in the conversation unless the learner has changed it.

ANTI-DUPLICATION
Never repeat the same learner-facing sentence or the same complete reply twice in one response. Do not echo your own previous reply. For START_LESSON, produce exactly one natural opening reply.{start_rule}

PROGRESS
Judge only the learner's latest message. Mark a target only when the learner genuinely produces its communicative meaning in the learning language. Natural wording differences are allowed. Do not mark something merely because you asked, displayed, translated, or mentioned it. Use only ids from the remaining list.

End every response with exactly one machine-readable marker, after the learner-facing text:
[[LESSON_PROGRESS:id1,id2]]
Use [[LESSON_PROGRESS:]] when no remaining target was practiced. Never mention the marker.
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


def _stream_lesson_response(*, request: LessonChatRequest, user_id: int, db: Session, native_language: str, target_language: str, level: str, curriculum: dict, conversation_id: str, profile_id: int) -> Generator[str, None, None]:
    progress = _get_or_create_practice_progress(user_id, profile_id, request.lesson_id, conversation_id, db)
    history = get_conversation_history(user_id=user_id, conversation_id=conversation_id, db=db, limit=MAX_HISTORY_MESSAGES)
    system_instruction = _build_system_instruction(native_language, target_language, level, curriculum, progress)
    messages = _build_contents(history, request.message)
    full_text = ""
    usage = (0, 0, 0)
    buffer = ""
    try:
        for chunk in provider.stream_text(
            system_instruction=system_instruction,
            contents=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            model=LESSON_TUTOR_MODEL,
        ):
            text = getattr(chunk, "text", None) if not isinstance(chunk, str) else chunk
            if text:
                full_text += text
                buffer += text
                while len(buffer) > STREAM_HOLD_CHARS:
                    emit = buffer[:-STREAM_HOLD_CHARS]
                    buffer = buffer[-STREAM_HOLD_CHARS:]
                    if emit:
                        yield sse_event("chunk", {"text": emit})
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage:
                usage = (
                    int(chunk_usage.get("prompt_tokens", usage[0]) or usage[0]),
                    int(chunk_usage.get("completion_tokens", usage[1]) or usage[1]),
                    int(chunk_usage.get("total_tokens", usage[2]) or usage[2]),
                )
        if buffer:
            yield sse_event("chunk", {"text": buffer})

        cleaned_text, completed_ids = _extract_progress_marker(full_text)
        cleaned_text = _remove_exact_duplicate_response(cleaned_text)
        valid_ids = {item["id"] for item in _lesson_target_sentences(curriculum)}
        practiced_ids = _update_practice_progress(
            progress=progress,
            conversation_id=conversation_id,
            completed_ids=completed_ids,
            valid_ids=valid_ids,
        )
        progress.completed = _lesson_completion(curriculum, progress)[0]
        db.commit()
        save_conversation_message(user_id=user_id, conversation_id=conversation_id, role="user", content=request.message, db=db)
        save_conversation_message(user_id=user_id, conversation_id=conversation_id, role="model", content=cleaned_text, db=db)
        record_api_usage(
            user_id=user_id,
            prompt_tokens=usage[0],
            completion_tokens=usage[1],
            total_tokens=usage[2],
            db=db,
            model=LESSON_TUTOR_MODEL,
        )
        yield sse_event("done", {"conversation_id": conversation_id, "text": cleaned_text, "completed": progress.completed, "practiced_count": len(practiced_ids), "target_count": len(valid_ids)})
    except Exception as exc:
        logger.exception("Lesson AI streaming failed: %s", exc)
        yield sse_event("error", {"message": str(exc)})


@router.post("/chat")
def lesson_chat(
    request: LessonChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.execute(
        select(LearningProfile).where(LearningProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning profile not found.")

    lesson = db.execute(
        select(CourseLesson).where(CourseLesson.id == request.lesson_id)
    ).scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    if lesson.language != profile.language:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson language does not match the learning profile.")

    curriculum = _load_lesson_curriculum(lesson)
    target_language = normalize_language(profile.language)
    native_language = normalize_language(current_user.native_language)
    level = normalize_level(lesson.level)
    if level is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid lesson level.")

    check_rate_limit(user_id=current_user.id)
    reserve_ai_request(user_id=current_user.id, db=db)

    conversation_id = request.conversation_id or str(uuid4())
    return StreamingResponse(
        _stream_lesson_response(
            request=request,
            user_id=current_user.id,
            db=db,
            native_language=native_language,
            target_language=target_language,
            level=level,
            curriculum=curriculum,
            conversation_id=conversation_id,
            profile_id=profile.id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
