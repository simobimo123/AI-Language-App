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
from services.ai.conversation import (
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

router = APIRouter(prefix="/ai/lesson", tags=["AI Lesson Tutor"])

logger = logging.getLogger(__name__)

LESSON_TUTOR_MODEL = AI_MODEL

MAX_HISTORY_MESSAGES = 20
MAX_LESSON_CONTEXT_CHARS = 1800
MAX_OUTPUT_TOKENS = 500

PROGRESS_MARKER = "[[LESSON_PROGRESS:"

# Correct regex:
# [[LESSON_PROGRESS:target_id]]
# or
# [[LESSON_PROGRESS:]]
PROGRESS_MARKER_RE = re.compile(
    r"\[\[LESSON_PROGRESS:([^\]\r\n]*)\]\]"
)

STREAM_HOLD_CHARS = 48

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


# ============================================================================
# LESSON LOADING
# ============================================================================


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
            path.read_text(encoding="utf-8-sig")
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

    lesson_data = data.get("lesson")

    if not isinstance(lesson_data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid lesson structure.",
        )

    return data


# ============================================================================
# LESSON TARGET ENGINE
# ============================================================================


def _lesson_data(curriculum: dict) -> dict:
    lesson = curriculum.get("lesson")
    return lesson if isinstance(lesson, dict) else {}


def _lesson_targets(curriculum: dict) -> list[dict]:
    """
    Read:

    lesson.targets = [
        {
            "id": "...",
            "order": 1,
            "required": true,
            "goal": "...",
            "patterns": [...],
            "suggestion": "...",
            "context": "..."
        }
    ]

    The backend keeps the complete target list internally.

    Only the current and immediate next target are sent to the AI.
    """

    lesson = _lesson_data(curriculum)

    raw_targets = lesson.get("targets", [])

    if not isinstance(raw_targets, list):
        return []

    targets: list[dict] = []
    seen_ids: set[str] = set()

    for index, raw in enumerate(raw_targets, start=1):
        if not isinstance(raw, dict):
            continue

        target_id = str(
            raw.get("id", f"target_{index}")
        ).strip()

        if not target_id or target_id in seen_ids:
            continue

        order = raw.get("order", index)

        try:
            order = int(order)
        except (TypeError, ValueError):
            order = index

        goal = raw.get("goal", "")

        if isinstance(goal, dict):
            goal = goal.get("description", "")

        goal = str(goal or "").strip()

        patterns = raw.get("patterns", [])

        if isinstance(patterns, str):
            patterns = [patterns]

        if not isinstance(patterns, list):
            patterns = []

        normalized_patterns = [
            str(pattern).strip()
            for pattern in patterns
            if str(pattern).strip()
        ]

        suggestion = raw.get("suggestion", "")

        if isinstance(suggestion, dict):
            suggestion = suggestion.get("text", "")

        suggestion = str(suggestion or "").strip()

        required = raw.get("required", True)
        required = bool(required)

        context = raw.get("context", "")

        if isinstance(context, dict):
            context = json.dumps(
                context,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        else:
            context = str(context or "").strip()

        targets.append(
            {
                "id": target_id,
                "order": order,
                "required": required,
                "goal": goal,
                "patterns": normalized_patterns,
                "suggestion": suggestion,
                "context": context,
            }
        )

        seen_ids.add(target_id)

    targets.sort(
        key=lambda item: (
            item["order"],
            item["id"],
        )
    )

    return targets


def _required_target_ids(curriculum: dict) -> list[str]:
    return [
        target["id"]
        for target in _lesson_targets(curriculum)
        if target.get("required", True)
    ]


# ============================================================================
# CONVERSATION CONTEXT
# ============================================================================


def _lesson_context(curriculum: dict) -> str:
    """
    Build a compact context.

    Do NOT send the whole JSON to the AI.
    """

    lesson = _lesson_data(curriculum)

    title = str(
        lesson.get("title", "")
    ).strip()

    language = str(
        lesson.get("language", "")
    ).strip()

    level = str(
        lesson.get("level", "")
    ).strip()

    conversation = lesson.get(
        "conversation",
        {},
    )

    if not isinstance(conversation, dict):
        conversation = {}

    mode = str(
        conversation.get(
            "mode",
            "guided_natural",
        )
    ).strip()

    entities = conversation.get(
        "entities",
        [],
    )

    compact_entities: list[dict] = []

    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue

            compact = {
                "id": str(
                    entity.get("id", "")
                ).strip(),
                "type": str(
                    entity.get("type", "")
                ).strip(),
                "name": str(
                    entity.get("name", "")
                ).strip(),
                "gender": str(
                    entity.get("gender", "")
                ).strip(),
            }

            compact = {
                key: value
                for key, value in compact.items()
                if value
            }

            if compact:
                compact_entities.append(compact)

    context = {
        "title": title,
        "language": language,
        "level": level,
        "mode": mode,
        "participants": [
            "tutor",
            "learner",
        ],
        "entities": compact_entities,
    }

    text = json.dumps(
        context,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return text[:MAX_LESSON_CONTEXT_CHARS]


# ============================================================================
# PROGRESS
# ============================================================================


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
                "practiced_target_ids": [],
            },
        )

        db.add(progress)
        db.flush()

        return progress

    state = (
        progress.practice_state
        if isinstance(progress.practice_state, dict)
        else {}
    )

    if state.get("conversation_id") != conversation_id:
        progress.practice_state = {
            "conversation_id": conversation_id,
            "practiced_target_ids": [],
        }

    return progress


def _practiced_target_ids(
    progress: UserLessonProgress,
) -> set[str]:
    state = (
        progress.practice_state
        if isinstance(progress.practice_state, dict)
        else {}
    )

    raw = state.get(
        "practiced_target_ids",
        [],
    )

    # Backwards compatibility.
    if not isinstance(raw, list):
        raw = state.get(
            "practiced_sentence_ids",
            [],
        )

    if not isinstance(raw, list):
        return set()

    return {
        str(value).strip()
        for value in raw
        if str(value).strip()
    }


def _update_practice_progress(
    *,
    progress: UserLessonProgress,
    conversation_id: str,
    completed_ids: set[str],
    targets: list[dict],
) -> set[str]:
    """
    Update only the current unfinished target.

    This is deliberately stricter than simply accepting every ID
    returned by the AI.

    The backend is the source of truth.
    """

    required_ids = [
        target["id"]
        for target in targets
        if target.get("required", True)
    ]

    current = (
        _practiced_target_ids(progress)
        & set(required_ids)
    )

    if not required_ids:
        progress.practice_state = {
            "conversation_id": conversation_id,
            "practiced_target_ids": [],
        }
        return set()

    # Find the first unfinished target.
    current_target_id = None

    for target_id in required_ids:
        if target_id not in current:
            current_target_id = target_id
            break

    # The AI may only complete the current unfinished target.
    if (
        current_target_id is not None
        and current_target_id in completed_ids
    ):
        current.add(current_target_id)

    progress.practice_state = {
        "conversation_id": conversation_id,
        "practiced_target_ids": [
            target_id
            for target_id in required_ids
            if target_id in current
        ],
    }

    return current


# ============================================================================
# TARGET TRACKING SENT TO AI
# ============================================================================


def _build_target_tracking_context(
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    """
    Send only the current target and the immediate next target.

    This intentionally keeps the prompt compact.
    """

    targets = _lesson_targets(curriculum)
    practiced = _practiced_target_ids(progress)

    required_targets = [
        target
        for target in targets
        if target.get("required", True)
    ]

    remaining = [
        target
        for target in required_targets
        if target["id"] not in practiced
    ]

    if not remaining:
        return json.dumps(
            {
                "current": None,
                "next": None,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    current = remaining[0]

    next_target = (
        remaining[1]
        if len(remaining) > 1
        else None
    )

    current_data = {
        "id": current["id"],
        "goal": current["goal"],
        "patterns": current["patterns"],
        "suggestion": current["suggestion"],
    }

    if current.get("context"):
        current_data["context"] = current["context"]

    next_data = None

    if next_target is not None:
        next_data = {
            "id": next_target["id"],
            "goal": next_target["goal"],
            "patterns": next_target["patterns"],
        }

    return json.dumps(
        {
            "current": current_data,
            "next": next_data,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


# ============================================================================
# SYSTEM PROMPT
# ============================================================================


def _build_system_instruction(
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    context = _lesson_context(curriculum)

    tracking = _build_target_tracking_context(
        curriculum,
        progress,
    )

    lesson = _lesson_data(curriculum)

    completion = lesson.get(
        "completion",
        {},
    )

    if not isinstance(completion, dict):
        completion = {}

    closing = completion.get(
        "closing",
        {},
    )

    if isinstance(closing, dict):
        closing_instruction = str(
            closing.get(
                "instruction",
                "Naturally close the conversation after all required targets are completed.",
            )
        ).strip()

        completion_signal = str(
            closing.get(
                "signal",
                "LESSON_COMPLETED",
            )
        ).strip()

    else:
        closing_instruction = (
            "Naturally close the conversation after all required targets are completed."
        )

        completion_signal = "LESSON_COMPLETED"

    return f"""
You are an AI tutor conducting a guided natural conversation practice.

Target language: {target_language}

Learner native language: {native_language}

CEFR level: {level}

LESSON CONTEXT

{context}

CURRENT TRAINING STATE

{tracking}

The lesson JSON is the source of truth.

==================================================
SPEAKERS
==================================================

There are ONLY TWO ACTIVE SPEAKERS:

1. You = the AI tutor.

2. The user = the learner.

Entities such as Thomas, Sarah, Anna, friends or family members
are NEVER active speakers.

They may only be mentioned, described, or discussed.

NEVER create dialogue for an entity.

Never write:

Thomas: ...

Sarah: ...

Never switch your identity to an entity.

==================================================
TRAINING
==================================================

Train the CURRENT target only.

The target is what the learner must practice.

Do not jump to the next target.

Do not reveal target IDs or internal progress.

Create a natural conversation around the current target.

The conversation is NOT a fixed script.

You may phrase your questions naturally as long as they create
a genuine opportunity for the learner to practice the current target.

The learner may use a different correct formulation when it fulfills
the communicative goal.

==================================================
SUGGESTIONS
==================================================

The suggestion in the current target is the INTENDED practice answer.

If the learner needs help, naturally guide them toward that answer.

Do not invent a different practice target.

Do not tell the learner that the suggestion is an internal curriculum rule.

==================================================
CORRECTION
==================================================

If the learner makes a mistake:

1. Briefly correct it.

2. Give a short correct model if useful.

3. Ask the learner to try again.

Do not give long grammar explanations.

If the learner is correct, continue naturally.

Do not force unnecessary repetitions.

==================================================
CONVERSATION
==================================================

You must lead the conversation.

Ask only ONE short question or request at a time.

Keep responses short, normally one or two sentences.

Do not restart the lesson.

Do not repeat the opening greeting.

Do not repeat an already answered question unless correction
is genuinely necessary.

Never invent the learner's personal information.

Never assume the learner's name, city, family, friends, or identity.

Use only information the learner actually provided.

If the learner goes off-topic, briefly acknowledge it and guide
the conversation back to the current target.

Do not turn the session into a grammar lecture.

==================================================
START
==================================================

If the user message is exactly:

START_LESSON

begin the conversation naturally.

Use the first unfinished target.

Do not mention START_LESSON.

Do not explain the lesson.

Do not complete multiple targets in one response.

==================================================
CONTINUITY
==================================================

The conversation history is persistent.

USER = learner.

ASSISTANT = AI tutor.

Never confuse an entity with the learner.

Never confuse the tutor with the learner.

Preserve information already established in the conversation.

==================================================
COMPLETION
==================================================

Do NOT end the lesson before all required targets are completed.

When all required targets have been completed:

1. Give ONE short natural closing sentence.

2. Do not start another topic.

3. Do not ask another practice question.

4. Internally signal completion using:

{completion_signal}

The closing is part of the user-facing conversation.

The backend decides whether the lesson is actually completed.

==================================================
PROGRESS MARKER
==================================================

At the END of every response output exactly one marker:

[[LESSON_PROGRESS:id]]

or:

[[LESSON_PROGRESS:]]

Only mark the CURRENT target.

Mark a learner target ONLY when the learner's latest message
actually demonstrates the target.

Never mark a learner target before the learner produces it.

Never mark a future target.

Never invent progress.

The marker is internal and must never be explained to the learner.

==================================================
CLOSING INSTRUCTION
==================================================

{closing_instruction}
""".strip()


# ============================================================================
# MESSAGE HISTORY
# ============================================================================


def _build_contents(
    history,
    message: str,
) -> list[dict[str, str]]:
    contents: list[dict[str, str]] = []

    for item in history:
        role = (
            "assistant"
            if item.role == "model"
            else item.role
        )

        if role not in {
            "user",
            "assistant",
            "system",
        }:
            role = "user"

        contents.append(
            {
                "role": role,
                "content": item.content,
            }
        )

    contents.append(
        {
            "role": "user",
            "content": message,
        }
    )

    return contents


# ============================================================================
# RESPONSE CLEANING
# ============================================================================


def _extract_progress_marker(
    text: str,
) -> tuple[str, set[str]]:
    matches = list(
        PROGRESS_MARKER_RE.finditer(text)
    )

    if not matches:
        return text.strip(), set()

    completed_ids: set[str] = set()

    for match in matches:
        raw_ids = match.group(1)

        for value in raw_ids.split(","):
            value = value.strip()

            if value:
                completed_ids.add(value)

    cleaned = PROGRESS_MARKER_RE.sub(
        "",
        text,
    ).strip()

    return cleaned, completed_ids


def _remove_exact_duplicate_response(
    text: str,
) -> str:
    cleaned = re.sub(
        r"[\u200b\u200c\u200d\ufeff]",
        "",
        text,
    ).strip()

    if not cleaned:
        return cleaned

    match = re.fullmatch(
        r"(.+?)\s+\1",
        cleaned,
        flags=re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    normalized = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    if (
        len(normalized) >= 4
        and len(normalized) % 2 == 0
    ):
        half = len(normalized) // 2

        if (
            normalized[:half].rstrip()
            == normalized[half:].lstrip()
        ):
            return normalized[:half].strip()

    return cleaned


# ============================================================================
# COMPLETION
# ============================================================================


def _lesson_completion(
    curriculum: dict,
    progress: UserLessonProgress,
) -> tuple[bool, int, int]:
    required_ids = set(
        _required_target_ids(curriculum)
    )

    if not required_ids:
        return False, 0, 0

    practiced_ids = (
        _practiced_target_ids(progress)
        & required_ids
    )

    return (
        required_ids.issubset(practiced_ids),
        len(practiced_ids),
        len(required_ids),
    )


def _completed_lesson_stream(
    conversation_id: str,
    practiced_count: int,
    target_count: int,
) -> Generator[str, None, None]:
    yield sse_event(
        "done",
        {
            "conversation_id": conversation_id,
            "completed": True,
            "conversation_completed": True,
            "assessment_unlocked": True,
            "next_action": "assessment",
            "practiced_targets": practiced_count,
            "target_targets": target_count,
        },
    )


# ============================================================================
# MAIN STREAM
# ============================================================================


def _stream_lesson_response(
    *,
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
    try:
        progress = _get_or_create_practice_progress(
            user_id,
            profile_id,
            request.lesson_id,
            conversation_id,
            db,
        )

        history = get_conversation_history(
            user_id=user_id,
            conversation_id=conversation_id,
            max_messages=MAX_HISTORY_MESSAGES,
            db=db,
        )

        system_instruction = _build_system_instruction(
            native_language=native_language,
            target_language=target_language,
            level=level,
            curriculum=curriculum,
            progress=progress,
        )

        messages = _build_contents(
            history,
            request.message,
        )

        full_text = ""

        usage = (
            0,
            0,
            0,
        )

        buffer = ""
        streamed_visible_text = ""

        for chunk in provider.stream_text(
            system_instruction=system_instruction,
            contents=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ):
            if isinstance(chunk, dict):
                text = str(
                    chunk.get(
                        "text",
                        "",
                    )
                    or ""
                )

                usage = (
                    chunk.get(
                        "usage",
                        usage,
                    )
                    or usage
                )

            else:
                text = str(
                    getattr(
                        chunk,
                        "text",
                        "",
                    )
                    or ""
                )

                chunk_usage = (
                    getattr(
                        chunk,
                        "prompt_tokens",
                        0,
                    )
                    or 0,
                    getattr(
                        chunk,
                        "completion_tokens",
                        0,
                    )
                    or 0,
                    getattr(
                        chunk,
                        "total_tokens",
                        0,
                    )
                    or 0,
                )

                if any(chunk_usage):
                    usage = chunk_usage

            if not text:
                continue

            full_text += text
            buffer += text

            marker_index = buffer.find(
                PROGRESS_MARKER
            )

            if marker_index >= 0:
                visible_text = buffer[
                    :marker_index
                ]

                buffer = ""

                if visible_text:
                    streamed_visible_text += visible_text

                    yield sse_event(
                        "token",
                        {
                            "text": visible_text,
                        },
                    )

                continue

            if len(buffer) > STREAM_HOLD_CHARS:
                emit = buffer[
                    :-STREAM_HOLD_CHARS
                ]

                buffer = buffer[
                    -STREAM_HOLD_CHARS:
                ]

                if emit:
                    streamed_visible_text += emit

                    yield sse_event(
                        "token",
                        {
                            "text": emit,
                        },
                    )

        cleaned_text, completed_ids = (
            _extract_progress_marker(
                full_text
            )
        )

        cleaned_text = (
            _remove_exact_duplicate_response(
                cleaned_text
            )
        )

        if not cleaned_text:
            raise RuntimeError(
                "AI tutor returned an empty response."
            )

        if cleaned_text.startswith(
            streamed_visible_text
        ):
            remaining_text = cleaned_text[
                len(streamed_visible_text):
            ]

            if remaining_text:
                yield sse_event(
                    "token",
                    {
                        "text": remaining_text,
                    },
                )

        else:
            # This is a safety fallback for unexpected cleanup differences.
            # Avoid sending duplicated text if part of the response was
            # already streamed.
            if cleaned_text != streamed_visible_text:
                yield sse_event(
                    "token",
                    {
                        "text": cleaned_text,
                    },
                )

        # ------------------------------------------------------------------
        # Save conversation
        # ------------------------------------------------------------------

        save_conversation_message(
            user_id,
            conversation_id,
            "user",
            request.message,
            db,
        )

        save_conversation_message(
            user_id,
            conversation_id,
            "assistant",
            cleaned_text,
            db,
        )

        # ------------------------------------------------------------------
        # Update target progress
        # ------------------------------------------------------------------

        targets = _lesson_targets(
            curriculum
        )

        _update_practice_progress(
            progress=progress,
            conversation_id=conversation_id,
            completed_ids=completed_ids,
            targets=targets,
        )

        db.commit()

        # ------------------------------------------------------------------
        # Usage
        # ------------------------------------------------------------------

        try:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            if isinstance(
                usage,
                (tuple, list),
            ):
                if len(usage) >= 1:
                    prompt_tokens = usage[0]

                if len(usage) >= 2:
                    completion_tokens = usage[1]

                if len(usage) >= 3:
                    total_tokens = usage[2]

            record_api_usage(
                user_id=user_id,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(total_tokens),
                db=db,
                model=LESSON_TUTOR_MODEL,
            )

        except Exception:
            logger.exception(
                "Failed to record lesson AI usage."
            )

        # ------------------------------------------------------------------
        # Completion
        # ------------------------------------------------------------------

        (
            completed,
            practiced_count,
            target_count,
        ) = _lesson_completion(
            curriculum,
            progress,
        )

        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "completed": completed,
                "conversation_completed": completed,
                "assessment_unlocked": completed,
                "next_action": (
                    "assessment"
                    if completed
                    else None
                ),
                "practiced_targets": practiced_count,
                "target_targets": target_count,
            },
        )

    except Exception as exc:
        logger.exception(
            "Lesson AI streaming failed: %s",
            exc,
        )

        try:
            db.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback lesson AI transaction."
            )

        yield sse_event(
            "error",
            {
                "message": str(exc),
            },
        )


# ============================================================================
# ROUTE
# ============================================================================


@router.post("/chat")
def lesson_chat(
    request: LessonChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id
            == current_user.id
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning profile not found.",
        )

    lesson = db.execute(
        select(CourseLesson).where(
            CourseLesson.id
            == request.lesson_id
        )
    ).scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    # Compare normalized language codes.
    profile_language = normalize_language(
        profile.language
    )

    lesson_language = normalize_language(
        lesson.language
    )

    if lesson_language != profile_language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Lesson language does not match "
                "the learning profile."
            ),
        )

    target_language = profile_language

    native_language = normalize_language(
        current_user.native_language
    )

    level = normalize_level(
        lesson.level
    )

    if level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson level.",
        )

    curriculum = _load_lesson_curriculum(
        lesson
    )

    targets = _lesson_targets(
        curriculum
    )

    if not targets:
        logger.error(
            "Lesson %s has no targets.",
            request.lesson_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Lesson has no training targets. "
                "Check lesson.targets."
            ),
        )

    required_targets = [
        target
        for target in targets
        if target.get("required", True)
    ]

    if not required_targets:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Lesson has no required training targets."
            ),
        )

    conversation_id = (
        request.conversation_id
        or f"lesson_{uuid4()}"
    )

    progress = _get_or_create_practice_progress(
        current_user.id,
        profile.id,
        request.lesson_id,
        conversation_id,
        db,
    )

    (
        completed,
        practiced_count,
        target_count,
    ) = _lesson_completion(
        curriculum,
        progress,
    )

    # Already completed: do not call the AI again.
    if completed:
        db.commit()

        return StreamingResponse(
            _completed_lesson_stream(
                conversation_id,
                practiced_count,
                target_count,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    check_rate_limit(
        user_id=current_user.id
    )

    usage = get_current_usage(
        user_id=current_user.id,
        db=db,
    )

    if usage.request_count >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI limit reached.",
        )

    reserve_ai_request(
        user_id=current_user.id,
        db=db,
    )

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
        },
    )