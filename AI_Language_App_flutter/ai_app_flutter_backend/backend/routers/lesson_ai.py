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
    expected_learner_responses: list[str] = []
    sections = curriculum.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            values = section.get("expected_learner_responses", [])
            if isinstance(values, list):
                expected_learner_responses.extend(
                    str(value).strip()
                    for value in values
                    if isinstance(value, str) and value.strip()
                )

    if not isinstance(raw, list) or not raw:
        collected: list[dict[str, str]] = []
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue
                values = section.get("target_sentences", [])
                if not isinstance(values, list):
                    continue
                for value in values:
                    if isinstance(value, str) and value.strip():
                        collected.append({"sentence": value.strip()})
        raw = collected

    def looks_like_learner_response(sentence: str) -> bool:
        normalized_sentence = re.sub(r"\s+", " ", sentence.strip().lower()).rstrip(".!?。！？")
        for pattern in expected_learner_responses:
            normalized_pattern = re.sub(r"\s+", " ", pattern.strip().lower()).rstrip(".!?。！？")
            if "..." in normalized_pattern:
                prefix, suffix = normalized_pattern.split("...", 1)
                if normalized_sentence.startswith(prefix.strip()) and normalized_sentence.endswith(suffix.strip()):
                    return True
            elif normalized_sentence == normalized_pattern:
                return True
        return False

    result: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_sentences: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if isinstance(item, str):
            sentence = item.strip()
            explicit_id = ""
            role = "learner" if looks_like_learner_response(sentence) else "assistant"
        elif isinstance(item, dict):
            sentence = str(item.get("sentence", item.get("text", ""))).strip()
            explicit_id = str(item.get("id", "")).strip()
            role = str(item.get("role", "")).strip().lower()
            if role not in {"assistant", "learner", "either"}:
                role = "learner" if looks_like_learner_response(sentence) else "assistant"
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
        result.append({"id": sentence_id, "sentence": sentence, "role": role})
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


def _update_practice_progress(*, progress: UserLessonProgress, conversation_id: str, completed_ids: set[str], ordered_ids: list[str]) -> set[str]:
    """Apply only a contiguous prefix of the curriculum path; later targets cannot be skipped."""
    current = _practiced_sentence_ids(progress) & set(ordered_ids)
    completed = completed_ids & set(ordered_ids)

    for target_id in ordered_ids:
        if target_id in current:
            continue
        if target_id in completed:
            current.add(target_id)
            continue
        break

    progress.practice_state = {
        "conversation_id": conversation_id,
        "practiced_sentence_ids": [target_id for target_id in ordered_ids if target_id in current],
    }
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
    """Return the ordered path, exposing the first unfinished target prominently."""
    targets = _lesson_target_sentences(curriculum)
    practiced = _practiced_sentence_ids(progress)
    remaining = [item for item in targets if item["id"] not in practiced]
    if not remaining:
        return json.dumps(
            {"next_target": None, "remaining_targets": []},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return json.dumps(
        {
            "next_target": remaining[0],
            "remaining_targets": remaining,
            "ordered_path": True,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


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

ORDERED CONVERSATION PATH
{targets}

The ordered conversation path is the backbone of this lesson. It is NOT a list to display to the learner. It is a sequence of conversation milestones that must be practiced in order.

STRICT PATH RULES
1. Always work on the FIRST unfinished target (`next_target`). Never jump to a later target just because it seems interesting or easier.
2. Do not introduce a person, topic, question, place, or story that is not needed for the current target or the lesson context.
3. Do not move to a later target until the current target has genuinely been practiced. Keep the conversation natural, but the order is mandatory.
4. If the next target has role `assistant`, naturally produce that target in your reply. You may add only a very short natural transition. Mark it only because YOU actually produced it.
5. If the next target has role `learner`, do NOT pretend the learner already said it. Ask or respond in a way that naturally elicits that target. Mark it only after the USER actually produces its communicative meaning.
6. If role is `either`, judge from the conversation who should naturally produce it, but still keep the target in order.
7. If the learner gives a different but correct natural wording with the same communicative meaning, it can count for a learner target. Do not force an exact memorized string unless the curriculum clearly requires exact wording.
8. Once a target is completed, continue naturally toward the NEW first unfinished target on the next turn. Never go backward to an already completed target unless a brief correction is genuinely necessary.
9. The target list is ordered. Do not use `remaining_targets` as permission to choose any item; only `next_target` is actionable.
10. When all targets are completed, give one short natural closing sentence and do not start a new topic or ask another unrelated question.

Use only the lesson context above. Guide the learner through a natural conversation while following the ordered path. Do not lecture, list vocabulary, explain grammar at length, or reveal internal curriculum data. Ask only one short question/request at a time and give the learner most of the speaking turns. Keep replies to one or two short sentences. Use the learning language; use the native language only for a very brief clarification when clearly necessary. If the learner makes an important mistake, correct it briefly and ask them to produce the corrected sentence.

CONVERSATION MEMORY AND PARTICIPANT IDENTITY
Treat the conversation history as persistent memory for this lesson.
There are two primary participants: the USER/learner and YOU/the AI tutor. Other people may be mentioned by either participant.
Never confuse the USER with the AI tutor or with another person mentioned in the conversation.

Infer personal facts from who said them, not from names appearing anywhere in the text:
- If a USER message says "Ich heiße X", "Mein Name ist X", or clearly identifies the user's name, X is the learner's name.
- If an ASSISTANT message says "Ich heiße X", "Mein Name ist X", or clearly identifies the tutor's name, X is the AI tutor's name.
- If a USER message says "Ich wohne in X" or otherwise states where they live, X is the learner's residence.
- If an ASSISTANT message says "Ich wohne in X" or otherwise states where the tutor lives, X is the tutor's residence.
- Facts explicitly stated by the USER about themselves take priority over guesses or assumptions.
- The AI tutor's statements about itself describe the tutor, not the learner.
- A person's name appearing in a greeting or question does not by itself mean that person is the learner.
- Never assign the account name, a curriculum character name, or another person's name to the learner unless the USER explicitly identifies themselves with that name.

Remember confirmed names, relationships, locations, and other relevant personal information from earlier turns. Do not ask the learner for information that they already provided. If the learner already answered a personal question, continue using that answer naturally instead of asking the same question again.
If the learner introduces a new name or corrects an earlier fact, use the newest explicit statement.
If the history contains an earlier assistant mistake about someone's identity, do not preserve the mistake as a fact; resolve identity from the speaker who originally stated the information.

CONTINUITY
Use the full conversation history provided separately. Continue naturally from it; never restart or ask for information already established in the conversation unless the learner has changed it.

ANTI-DUPLICATION
Never repeat the same learner-facing sentence or the same complete reply twice in one response. Do not echo your own previous reply. For START_LESSON, produce exactly one natural opening reply.{start_rule}

PROGRESS MARKER
Judge progress against ONLY the first unfinished target.
- For an `assistant` target, mark its id only if you actually produced that target in this response.
- For a `learner` target, mark its id only if the USER's latest message genuinely produced its communicative meaning.
- For an `either` target, mark its id only when the corresponding communicative target was genuinely practiced by the appropriate speaker.
- You may mark consecutive assistant targets only when they were all genuinely produced in this response without skipping an unfinished learner target.
- Never mark a later target while an earlier target remains unfinished.
- Never invent completion just to make progress.

End every response with exactly one machine-readable marker, after the learner-facing text:
[[LESSON_PROGRESS:id1,id2]]
Use [[LESSON_PROGRESS:]] when no target was completed in this turn. Never mention the marker.
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
    history = get_conversation_history(
        user_id=user_id,
        conversation_id=conversation_id,
        max_messages=MAX_HISTORY_MESSAGES,
        db=db,
    )
    system_instruction = _build_system_instruction(native_language, target_language, level, curriculum, progress)
    messages = _build_contents(history, request.message)
    full_text = ""
    usage = (0, 0, 0)
    buffer = ""
    streamed_visible_text = ""
    try:
        for chunk in provider.stream_text(
            system_instruction=system_instruction,
            contents=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ):
            if isinstance(chunk, dict):
                text = str(chunk.get("text", "") or "")
                usage = chunk.get("usage", usage) or usage
            else:
                text = str(getattr(chunk, "text", "") or "")
                chunk_usage = (
                    getattr(chunk, "prompt_tokens", 0) or 0,
                    getattr(chunk, "completion_tokens", 0) or 0,
                    getattr(chunk, "total_tokens", 0) or 0,
                )
                if any(chunk_usage):
                    usage = chunk_usage
            if not text:
                continue
            full_text += text
            buffer += text
            marker_index = buffer.find(PROGRESS_MARKER)
            if marker_index >= 0:
                learner_text = buffer[:marker_index]
                buffer = ""
                if learner_text:
                    streamed_visible_text += learner_text
                    yield sse_event("token", {"text": learner_text})
                continue
            if len(buffer) > STREAM_HOLD_CHARS:
                emit = buffer[:-STREAM_HOLD_CHARS]
                buffer = buffer[-STREAM_HOLD_CHARS:]
                if emit:
                    streamed_visible_text += emit
                    yield sse_event("token", {"text": emit})
                continue

        cleaned_text, completed_ids = _extract_progress_marker(full_text)
        cleaned_text = _remove_exact_duplicate_response(cleaned_text)

        if cleaned_text.startswith(streamed_visible_text):
            remaining_text = cleaned_text[len(streamed_visible_text):]
            if remaining_text:
                yield sse_event("token", {"text": remaining_text})

        save_conversation_message(user_id, conversation_id, "user", request.message, db)
        if cleaned_text:
            save_conversation_message(user_id, conversation_id, "assistant", cleaned_text, db)
        ordered_ids = [item["id"] for item in _lesson_target_sentences(curriculum)]
        _update_practice_progress(
            progress=progress,
            conversation_id=conversation_id,
            completed_ids=completed_ids,
            ordered_ids=ordered_ids,
        )
        db.commit()
        try:
            prompt_tokens, completion_tokens, total_tokens = usage
            record_api_usage(
                user_id=user_id,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(total_tokens),
                db=db,
                model=LESSON_TUTOR_MODEL,
            )
        except Exception:
            logger.exception("Failed to record lesson AI usage.")
        completed, practiced_count, target_count = _lesson_completion(curriculum, progress)
        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "completed": completed,
                "practiced_sentences": practiced_count,
                "target_sentences": target_count,
            },
        )
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

    target_language = normalize_language(profile.language)
    native_language = normalize_language(current_user.native_language)
    level = normalize_level(lesson.level)
    if level is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid lesson level.")

    curriculum = _load_lesson_curriculum(lesson)
    check_rate_limit(user_id=current_user.id)
    usage = get_current_usage(user_id=current_user.id, db=db)
    if usage.request_count >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI limit reached.",
        )
    reserve_ai_request(user_id=current_user.id, db=db)

    conversation_id = request.conversation_id or f"lesson_{uuid4()}"
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
