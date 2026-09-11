from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import (
    CourseLesson,
    LearningProfile,
    LessonPracticeScenario,
    LessonTarget,
    LessonTargetPattern,
    User,
    UserLessonStageProgress,
)
from routers.auth import get_current_user
from services.ai.conversation import (
    get_conversation_history,
    save_conversation_message,
)
from services.ai.provider import AI_MODEL, provider
from services.ai.usage import record_api_usage


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/lesson", tags=["Lesson AI"])


MAX_HISTORY_MESSAGES = 40
MAX_HISTORY_CHARS_PER_MESSAGE = 1800
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 420

REPETITION_HISTORY_MESSAGES = 4
REPETITION_MIN_WORDS = 6
REPETITION_SIMILARITY_THRESHOLD = 0.78
REPETITION_PREFIX_THRESHOLD = 0.72
REPETITION_COMMON_SEQUENCE_THRESHOLD = 0.70


TARGET_COMPLETE_PATTERN = re.compile(
    r"\[\[TARGET_COMPLETE:(\d+)\]\]",
    re.IGNORECASE,
)

TEACHING_COMPLETE_PATTERN = re.compile(
    r"\[\[TEACHING_COMPLETE\]\]",
    re.IGNORECASE,
)


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )


def sse_event(event: str, data: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found.",
        )
    return lesson


def _get_profile(
    db: Session,
    user: User,
    lesson: CourseLesson,
) -> LearningProfile:
    profile = db.scalar(
        select(LearningProfile).where(
            LearningProfile.user_id == user.id,
            LearningProfile.language == lesson.language,
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="Learning profile not found for this lesson language.",
        )
    return profile


def _get_stage_progress(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
) -> UserLessonStageProgress:
    progress = db.scalar(
        select(UserLessonStageProgress).where(
            UserLessonStageProgress.user_id == user.id,
            UserLessonStageProgress.learning_profile_id == profile.id,
            UserLessonStageProgress.lesson_id == lesson.id,
        )
    )

    if progress is None:
        progress = UserLessonStageProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            teaching_status="available",
            practice_status="locked",
        )
        db.add(progress)
        db.flush()

    elif progress.teaching_status == "locked":
        progress.teaching_status = "available"

    if (
        progress.teaching_status == "completed"
        and progress.practice_status == "locked"
    ):
        progress.practice_status = "available"

    return progress


def _ensure_stage_open(
    progress: UserLessonStageProgress,
    stage: str,
) -> None:
    current = getattr(progress, f"{stage}_status")

    if current == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Stage '{stage}' is locked until "
                "the previous stage is completed."
            ),
        )

    if current == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage '{stage}' is already completed.",
        )


def _new_stage_conversation_id(
    progress: UserLessonStageProgress,
    stage: str,
) -> str:
    conversation_id = f"lesson_{stage}_{uuid4()}"

    setattr(
        progress,
        f"{stage}_conversation_id",
        conversation_id,
    )

    return conversation_id


def _get_canonical_conversation_id(
    progress: UserLessonStageProgress,
    stage: str,
) -> str:
    field_name = f"{stage}_conversation_id"
    prefix = f"lesson_{stage}_"

    current = str(
        getattr(progress, field_name, "") or ""
    ).strip()

    if current and current.startswith(prefix):
        return current

    return _new_stage_conversation_id(
        progress,
        stage,
    )


def _targets(
    db: Session,
    lesson_id: int,
) -> list[dict]:
    rows = db.scalars(
        select(LessonTarget)
        .where(LessonTarget.lesson_id == lesson_id)
        .order_by(LessonTarget.target_order)
    ).all()

    result: list[dict] = []

    for row in rows:
        patterns = db.scalars(
            select(LessonTargetPattern)
            .where(LessonTargetPattern.target_id == row.id)
            .order_by(LessonTargetPattern.id)
        ).all()

        result.append(
            {
                "order": row.target_order,
                "goal": row.goal,
                "patterns": [
                    pattern.pattern
                    for pattern in patterns[:2]
                ],
                "required": row.required,
            }
        )

    return result


def _practice_context(
    db: Session,
    lesson_id: int,
) -> dict | None:
    row = db.scalar(
        select(LessonPracticeScenario)
        .where(LessonPracticeScenario.lesson_id == lesson_id)
        .order_by(LessonPracticeScenario.scenario_order)
    )

    if row is None:
        return None

    return {
        "title": str(row.title or "").strip()[:120],
        "context": str(row.context or "").strip()[:300],
        "instructions": str(row.instructions or "").strip()[:300],
    }


def _remove_control_markers(text: str) -> str:
    cleaned = TARGET_COMPLETE_PATTERN.sub("", text)
    cleaned = TEACHING_COMPLETE_PATTERN.sub("", cleaned)

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def _normalize_for_repetition(text: str) -> str:
    value = _remove_control_markers(text)
    value = re.sub(r"\s+", " ", value).strip().lower()

    value = re.sub(
        r"[^\w\s\u00C0-\uFFFF]",
        "",
        value,
    )

    return value


def _normalized_words(text: str) -> list[str]:
    value = _normalize_for_repetition(text)
    if not value:
        return []

    return value.split()


def _deduplicate_adjacent_sentences(text: str) -> str:
    cleaned = _remove_control_markers(text)

    if not cleaned:
        return cleaned

    parts = re.split(
        r"(?<=[.!?。！？])\s+",
        cleaned,
    )

    result: list[str] = []
    previous_key = ""

    for part in parts:
        piece = part.strip()

        if not piece:
            continue

        key = _normalize_for_repetition(piece)

        if key and key == previous_key:
            continue

        result.append(piece)
        previous_key = key

    return " ".join(result).strip()


def _longest_common_word_run(
    first: list[str],
    second: list[str],
) -> int:
    if not first or not second:
        return 0

    matcher = SequenceMatcher(
        None,
        first,
        second,
    )

    longest = 0

    for block in matcher.get_matching_blocks():
        if block.size > longest:
            longest = block.size

    return longest


def _assistant_repetition_score(
    reply: str,
    previous_reply: str,
) -> tuple[float, float, float]:
    reply_key = _normalize_for_repetition(reply)
    previous_key = _normalize_for_repetition(previous_reply)

    if not reply_key or not previous_key:
        return 0.0, 0.0, 0.0

    reply_words = reply_key.split()
    previous_words = previous_key.split()

    similarity = SequenceMatcher(
        None,
        reply_key,
        previous_key,
    ).ratio()

    prefix_length = 0

    for current_word, previous_word in zip(
        reply_words,
        previous_words,
    ):
        if current_word != previous_word:
            break
        prefix_length += 1

    max_prefix_base = max(
        min(len(reply_words), 12),
        1,
    )

    prefix_ratio = (
        prefix_length / max_prefix_base
        if max_prefix_base
        else 0.0
    )

    common_run = _longest_common_word_run(
        reply_words,
        previous_words,
    )

    common_run_ratio = (
        common_run / min(len(reply_words), len(previous_words))
        if min(len(reply_words), len(previous_words)) > 0
        else 0.0
    )

    return (
        similarity,
        prefix_ratio,
        common_run_ratio,
    )


def _is_repeated_assistant_reply(
    reply: str,
    history,
) -> bool:
    reply_key = _normalize_for_repetition(reply)

    if not reply_key:
        return False

    reply_words = reply_key.split()

    if len(reply_words) < REPETITION_MIN_WORDS:
        return False

    recent_assistant = [
        item
        for item in history
        if item.role in {"assistant", "model"}
        and str(item.content or "").strip()
    ]

    if not recent_assistant:
        return False

    for item in recent_assistant[-REPETITION_HISTORY_MESSAGES:]:
        previous_reply = str(item.content or "").strip()

        if not previous_reply:
            continue

        similarity, prefix_ratio, common_run_ratio = (
            _assistant_repetition_score(
                reply,
                previous_reply,
            )
        )

        previous_words = _normalized_words(previous_reply)

        if len(previous_words) < REPETITION_MIN_WORDS:
            continue

        if similarity >= REPETITION_SIMILARITY_THRESHOLD:
            return True

        if prefix_ratio >= REPETITION_PREFIX_THRESHOLD:
            return True

        if (
            common_run_ratio
            >= REPETITION_COMMON_SEQUENCE_THRESHOLD
            and len(reply_words) >= REPETITION_MIN_WORDS
        ):
            return True

    return False


def _history_messages(history) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = (
            "assistant"
            if item.role == "model"
            else item.role
        )

        if role not in {"user", "assistant"}:
            continue

        content = str(item.content or "").strip()

        if not content:
            continue

        content = _remove_control_markers(content)

        if not content:
            continue

        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = (
                content[:MAX_HISTORY_CHARS_PER_MESSAGE]
                .rstrip()
                + "…"
            )

        result.append(
            {
                "role": role,
                "content": content,
            }
        )

    return result


def _completed_target_orders(history) -> list[int]:
    completed: set[int] = set()

    for item in history:
        if item.role not in {"assistant", "model"}:
            continue

        content = str(item.content or "")

        for match in TARGET_COMPLETE_PATTERN.finditer(content):
            try:
                target_order = int(match.group(1))
            except ValueError:
                continue

            if target_order > 0:
                completed.add(target_order)

    return sorted(completed)


def _current_target_order(
    targets: list[dict],
    history,
) -> int | None:
    required_orders = [
        int(target["order"])
        for target in targets
        if target["required"]
        and target.get("order") is not None
    ]

    if not required_orders:
        return None

    completed = set(
        _completed_target_orders(history)
    )

    for order in required_orders:
        if order not in completed:
            return order

    return None


def _all_required_targets_completed(
    targets: list[dict],
    completed_orders: set[int],
) -> bool:
    required_orders = {
        int(target["order"])
        for target in targets
        if target["required"]
        and target.get("order") is not None
    }

    if not required_orders:
        return False

    return required_orders.issubset(completed_orders)


def _target_by_order(
    targets: list[dict],
    target_order: int | None,
) -> dict | None:
    if target_order is None:
        return None

    for target in targets:
        if (
            target["required"]
            and target.get("order") is not None
            and int(target["order"]) == target_order
        ):
            return target

    return None


def _compact_goals(
    targets: list[dict],
) -> str:
    lines: list[str] = []

    for target in targets:
        if not target["required"]:
            continue

        goal = str(
            target["goal"] or ""
        ).strip()

        patterns = [
            str(item).strip()
            for item in target["patterns"]
            if str(item).strip()
        ]

        if not goal and not patterns:
            continue

        order = target.get("order")

        prefix = (
            f"{order}. "
            if order is not None
            else "- "
        )

        if patterns:
            if goal:
                lines.append(
                    f"{prefix}{goal} | "
                    f"{' | '.join(patterns)}"
                )
            else:
                lines.append(
                    f"{prefix}{' | '.join(patterns)}"
                )
        else:
            lines.append(
                f"{prefix}{goal}"
            )

    return (
        "\n".join(lines)
        or "- Follow the lesson objectives."
    )


def _prompt_context(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    current_target_order: int | None = None,
) -> str:
    context = (
        f"Language: {lesson.language}\n"
        f"Level: {lesson.level}\n"
    )

    if current_target_order is not None:
        current_target = _target_by_order(
            targets,
            current_target_order,
        )

        if current_target is not None:
            goal = str(
                current_target["goal"] or ""
            ).strip()

            patterns = [
                str(item).strip()
                for item in current_target["patterns"]
                if str(item).strip()
            ]

            context += (
                f"Current objective: "
                f"{goal or 'Follow the current lesson objective.'}\n"
            )

            if patterns:
                context += (
                    f"Useful language: "
                    f"{' | '.join(patterns[:2])}\n"
                )
        else:
            context += (
                "Current objective: "
                "Follow the current lesson objective.\n"
            )
    else:
        context += (
            "Teaching targets:\n"
            f"{_compact_goals(targets)}\n"
        )

    if scenario:
        title = str(
            scenario.get("title", "")
        ).strip()

        scenario_context = str(
            scenario.get("context", "")
        ).strip()

        instructions = str(
            scenario.get("instructions", "")
        ).strip()

        scenario_parts = [
            part
            for part in (
                title,
                scenario_context,
                instructions,
            )
            if part
        ]

        if scenario_parts:
            context += (
                "Practice scenario: "
                + " ".join(scenario_parts)
                + "\n"
            )

    return context.strip()


def _teaching_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    current_target_order: int | None,
    is_start: bool,
) -> str:
    current_target = _target_by_order(
        targets,
        current_target_order,
    )

    if current_target is None:
        current_target_text = (
            "There is no remaining learning objective."
        )
    else:
        goal = str(
            current_target["goal"] or ""
        ).strip()

        patterns = [
            str(item).strip()
            for item in current_target["patterns"]
            if str(item).strip()
        ]

        current_target_text = (
            f"Current objective: "
            f"{goal or 'Teach the current lesson objective.'}"
        )

        if patterns:
            current_target_text += (
                "\nUseful language: "
                f"{' | '.join(patterns[:2])}"
            )

    if is_start:
        turn_rule = (
            "This is the beginning of the stage. "
            "Start naturally with the current objective. "
            "Use one short example OR one simple question, "
            "then ask the learner to respond."
        )
    else:
        turn_rule = (
            "This is an ongoing lesson. "
            "Respond primarily to the learner's latest message. "
            "Continue from the current objective. "
            "Never restart the lesson."
        )

    return f"""
You are a friendly language teacher teaching one learner.

LANGUAGE
{lesson.language}

LEVEL
{lesson.level}

{current_target_text}

PRIMARY GOAL
Teach the current objective through a natural teacher-learner interaction.

NON-NEGOTIABLE RULES
1. Respond to the learner's latest message first.
2. Never invent, guess, infer, replace, translate, or alter a learner fact.
3. A learner fact is valid only when the learner explicitly provided it.
4. Never treat your own previous statements as facts about the learner.
5. Never invent the learner's name.
6. Never turn one learner name into another name.
7. If the learner gives a name, preserve the exact form they gave.
8. Never invent a learner answer.
9. Never answer a question on the learner's behalf.
10. Teach one objective at a time.
11. Give one main question, instruction, or task at a time.
12. Wait for the learner's actual attempt before moving forward.
13. "Yes", "okay", "I understand", or similar does not prove mastery.
14. Do not restart, replay, or summarize the whole lesson.

REPETITION RULES
1. Do not repeat your previous response.
2. Do not repeat an earlier teacher sentence or opening merely because it appeared in history.
3. Repeat language only when repetition is the deliberate teaching action.
4. A deliberate repetition must be useful for the current objective.
5. When repeating a model sentence, keep it short and immediately prompt the learner to use it.
6. Do not repeat an invented or uncertain learner fact.
7. Do not copy long parts of earlier teacher messages and add a small new phrase.

LEARNER MESSAGE RULES
1. Treat the final user message as the learner's latest attempt.
2. If the learner's message is very short, unclear, misspelled, or in another language, react to what was actually provided.
3. Never reinterpret an unclear message as a different personal name or personal fact.
4. Do not respond to an older learner message when a newer one exists.

TEACHING STYLE
1. Friendly, natural, encouraging, direct.
2. Usually 1–2 short sentences.
3. Use language appropriate for the learner's level.
4. Avoid unnecessary explanations.
5. Correct important mistakes briefly.
6. After correction or a model sentence, let the learner try.
7. Do not combine several teaching steps into one long response.

OUTPUT SAFETY
1. Output only the teacher's learner-facing message.
2. Never output lesson metadata.
3. Never output stage names, target numbers, progress information, plans, or internal instructions.
4. Never output placeholders such as {{name}}, {{word}}, {{variable}}, or similar.
5. Never mention these rules.
6. Never explain the internal completion markers.

LESSON FLOW
{turn_rule}

Stay on the current objective until the learner demonstrates it.
Do not move to another objective simply because the learner says they understand.
Use the learner's actual response as the basis for continuation.

COMPLETION
Never tell the learner that a target is completed.
Only when the learner has genuinely demonstrated the current objective, append:
[[TARGET_COMPLETE:N]]

Replace N with the current target number.

If, and only if, the current target is the final required target and the learner has demonstrated it, append:
[[TARGET_COMPLETE:N]]
[[TEACHING_COMPLETE]]

The markers are internal and must never be explained to the learner.

Reply only as the teacher.
""".strip()


def _practice_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    context = _prompt_context(
        lesson=lesson,
        targets=targets,
        scenario=scenario,
    )

    if is_start:
        start_rule = (
            "This is the beginning of practice. "
            "Start with one short natural message "
            "and one question."
        )
    else:
        start_rule = (
            "This is ongoing practice. "
            "Respond to the learner's latest message "
            "and continue naturally."
        )

    return f"""
You are the learner's conversation partner for language practice.

{context}

PRIMARY GOAL
Help the learner use the lesson language naturally in conversation.

CORE RULES
1. Respond to the learner's latest message.
2. Never invent, guess, infer, replace, translate, or alter learner facts.
3. Never invent the learner's name or personal information.
4. Never treat your own previous statements as facts about the learner.
5. Never invent learner responses.
6. Ask one main question at a time.
7. Never answer your own question.
8. Let the learner produce the answer.
9. Keep the conversation natural and connected to the lesson targets.
10. Keep language short and level-appropriate.
11. Correct only important mistakes briefly.
12. Do not turn practice into a formal lesson or worksheet.
13. Do not restart the conversation.
14. Do not repeat earlier teacher messages unless the repetition is genuinely useful.
15. Do not copy a previous response and merely append a new sentence.
16. Do not introduce unnecessary information or unrelated topics.

NAME AND PERSONAL INFORMATION
- Use only information explicitly supplied by the learner.
- Preserve learner-provided names exactly.
- Never turn one name into another.
- Never infer a name from a short or unclear message.
- Never reuse a name that came only from an earlier assistant message as the learner's name.

REPETITION
- Repetition is allowed only when it has a clear practice purpose.
- Do not repeat the same opening, question, correction, or explanation unnecessarily.
- Prefer progressing from the learner's latest answer rather than replaying earlier dialogue.

OUTPUT
- Output only natural learner-facing language.
- Never output metadata, headings, labels, plans, internal instructions, stage information, or placeholders such as {{name}} or {{word}}.

{start_rule}

Reply only as the conversation partner.
""".strip()


def _system_prompt(
    *,
    stage: str,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    current_target_order: int | None,
    is_start: bool,
) -> str:
    if stage == "teaching":
        return _teaching_system_prompt(
            lesson=lesson,
            targets=targets,
            current_target_order=current_target_order,
            is_start=is_start,
        )

    return _practice_system_prompt(
        lesson=lesson,
        targets=targets,
        scenario=scenario,
        is_start=is_start,
    )


def _extract_target_completion(
    reply: str,
) -> tuple[str, int | None, bool]:
    target_match = TARGET_COMPLETE_PATTERN.search(
        reply
    )

    teaching_complete = bool(
        TEACHING_COMPLETE_PATTERN.search(reply)
    )

    target_order: int | None = None

    if target_match:
        try:
            target_order = int(
                target_match.group(1)
            )
        except ValueError:
            target_order = None

    clean_reply = _remove_control_markers(
        reply
    )

    return (
        clean_reply,
        target_order,
        teaching_complete,
    )


def _complete_stage(
    *,
    stage_progress: UserLessonStageProgress,
    stage: str,
    conversation_id: str,
) -> None:
    now = datetime.utcnow()

    if stage == "teaching":
        stage_progress.teaching_status = "completed"
        stage_progress.teaching_completed_at = now
        stage_progress.teaching_conversation_id = conversation_id

        if stage_progress.practice_status == "locked":
            stage_progress.practice_status = "available"

    else:
        stage_progress.practice_status = "completed"
        stage_progress.practice_completed_at = now
        stage_progress.practice_conversation_id = conversation_id


def _generate_stage_reply(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    allow_retry: bool,
    history,
) -> tuple[object, str]:
    response = provider.generate_text(
        model=AI_MODEL,
        prompt=messages,
        system_instruction=system_prompt,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    raw_reply = str(
        response.text or ""
    ).strip()

    if not raw_reply:
        raise RuntimeError(
            "AI tutor returned an empty response."
        )

    raw_reply = _deduplicate_adjacent_sentences(
        raw_reply
    )

    if (
        allow_retry
        and _is_repeated_assistant_reply(
            raw_reply,
            history,
        )
    ):
        retry_prompt = (
            f"{system_prompt}\n\n"
            "FINAL RESPONSE CHECK:\n"
            "Your candidate response repeated wording from an earlier "
            "teacher response.\n"
            "Generate a new concise response.\n"
            "Respond to the learner's latest message only.\n"
            "Do not restart the lesson.\n"
            "Do not repeat the previous opening.\n"
            "Do not repeat earlier wording unless the current teaching "
            "objective explicitly requires deliberate repetition.\n"
            "Never invent learner facts or names."
        )

        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=retry_prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        raw_reply = str(
            response.text or ""
        ).strip()

        if not raw_reply:
            raise RuntimeError(
                "AI tutor returned an empty response."
            )

        raw_reply = _deduplicate_adjacent_sentences(
            raw_reply
        )

    return response, raw_reply


def _stream_stage_response(
    *,
    request: StageChatRequest,
    user_id: int,
    profile_id: int,
    lesson_id: int,
    conversation_id: str,
):
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is None:
            raise RuntimeError(
                "User not found."
            )

        lesson = _get_lesson(
            db,
            lesson_id,
        )

        profile = db.get(
            LearningProfile,
            profile_id,
        )

        if profile is None:
            raise RuntimeError(
                "Learning profile not found."
            )

        stage_progress = _get_stage_progress(
            db,
            user,
            profile,
            lesson,
        )

        _ensure_stage_open(
            stage_progress,
            request.stage,
        )

        is_control_message = (
            request.message == "START_STAGE"
        )

        if is_control_message:
            conversation_id = _new_stage_conversation_id(
                stage_progress,
                request.stage,
            )
            history = []

        else:
            canonical_conversation_id = (
                _get_canonical_conversation_id(
                    stage_progress,
                    request.stage,
                )
            )

            if canonical_conversation_id != conversation_id:
                conversation_id = canonical_conversation_id

            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=MAX_HISTORY_MESSAGES,
                db=db,
            )

        if (
            request.stage == "practice"
            and stage_progress.teaching_status != "completed"
        ):
            raise RuntimeError(
                "Practice requires completed AI teaching."
            )

        targets = _targets(
            db,
            lesson.id,
        )

        required_targets = [
            target
            for target in targets
            if target["required"]
        ]

        if not required_targets:
            raise RuntimeError(
                "Lesson has no required training targets."
            )

        current_target_order = None

        if request.stage == "teaching":
            current_target_order = _current_target_order(
                targets,
                history,
            )

            if current_target_order is None:
                completed_orders = set(
                    _completed_target_orders(
                        history
                    )
                )

                if _all_required_targets_completed(
                    targets,
                    completed_orders,
                ):
                    _complete_stage(
                        stage_progress=stage_progress,
                        stage="teaching",
                        conversation_id=conversation_id,
                    )

                    db.commit()

                    yield sse_event(
                        "done",
                        {
                            "conversation_id": conversation_id,
                            "stage": "teaching",
                            "axis_completed": True,
                            "lesson_completed": False,
                            "action": "AXIS_COMPLETE",
                            "target_id": None,
                            "confidence": None,
                        },
                    )

                    return

                current_target_order = int(
                    required_targets[0]["order"]
                )

        messages = _history_messages(
            history
        )

        if not is_control_message:
            messages.append(
                {
                    "role": "user",
                    "content": request.message[
                        :MAX_LEARNER_MESSAGE_CHARS
                    ],
                }
            )

        scenario = (
            _practice_context(
                db,
                lesson.id,
            )
            if request.stage == "practice"
            else None
        )

        system_prompt = _system_prompt(
            stage=request.stage,
            lesson=lesson,
            targets=targets,
            scenario=scenario,
            current_target_order=current_target_order,
            is_start=is_control_message,
        )

        response, raw_reply = _generate_stage_reply(
            system_prompt=system_prompt,
            messages=messages,
            allow_retry=(
                request.stage == "teaching"
                and not is_control_message
            ),
            history=history,
        )

        (
            reply,
            completed_target_order,
            teaching_complete_marker,
        ) = _extract_target_completion(
            raw_reply
        )

        if not reply:
            raise RuntimeError(
                "AI tutor returned no visible learner-facing text."
            )

        valid_target_completion = False

        if request.stage == "teaching":
            if completed_target_order is not None:
                if (
                    current_target_order is not None
                    and completed_target_order == current_target_order
                ):
                    valid_target_completion = True

        exchange_count_after = sum(
            1
            for item in history
            if item.role == "user"
        )

        if not is_control_message:
            exchange_count_after += 1

            save_conversation_message(
                user.id,
                conversation_id,
                "user",
                request.message[
                    :MAX_LEARNER_MESSAGE_CHARS
                ],
                db,
            )

        stored_assistant_reply = reply

        if valid_target_completion:
            stored_assistant_reply = (
                f"{reply}\n"
                f"[[TARGET_COMPLETE:{completed_target_order}]]"
            )

            completed_orders = set(
                _completed_target_orders(
                    history
                )
            )

            completed_orders.add(
                completed_target_order
            )

            if _all_required_targets_completed(
                targets,
                completed_orders,
            ):
                stored_assistant_reply += (
                    "\n[[TEACHING_COMPLETE]]"
                )

                teaching_complete_marker = True

        save_conversation_message(
            user.id,
            conversation_id,
            "assistant",
            stored_assistant_reply,
            db,
        )

        stage_completed = False

        if request.stage == "teaching":
            completed_orders = set(
                _completed_target_orders(
                    history
                )
            )

            if valid_target_completion:
                completed_orders.add(
                    completed_target_order
                )

            if (
                teaching_complete_marker
                and _all_required_targets_completed(
                    targets,
                    completed_orders,
                )
            ):
                _complete_stage(
                    stage_progress=stage_progress,
                    stage="teaching",
                    conversation_id=conversation_id,
                )

                stage_completed = True

        db.commit()

        try:
            record_api_usage(
                user_id=user.id,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens,
                db=db,
                model=AI_MODEL,
            )
        except Exception:
            logger.exception(
                "Failed to record lesson AI usage."
            )

        next_target_order = None

        if request.stage == "teaching":
            completed_orders = set(
                _completed_target_orders(
                    history
                )
            )

            if valid_target_completion:
                completed_orders.add(
                    completed_target_order
                )

            if not stage_completed:
                required_orders = [
                    int(target["order"])
                    for target in required_targets
                ]

                for order in required_orders:
                    if order not in completed_orders:
                        next_target_order = order
                        break

        yield sse_event(
            "conversation",
            {
                "conversation_id": conversation_id,
            },
        )

        yield sse_event(
            "token",
            {
                "text": reply,
            },
        )

        if request.stage == "teaching":
            if stage_completed:
                action = "AXIS_COMPLETE"
            elif valid_target_completion:
                action = "TARGET_COMPLETE"
            else:
                action = "CONTINUE"

            yield sse_event(
                "decision",
                {
                    "action": action,
                    "target_id": (
                        completed_target_order
                        if valid_target_completion
                        else None
                    ),
                    "next_target_id": next_target_order,
                    "confidence": None,
                },
            )

        else:
            yield sse_event(
                "decision",
                {
                    "action": "CONTINUE",
                    "target_id": None,
                    "confidence": None,
                },
            )

        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "stage": request.stage,
                "axis_completed": stage_completed,
                "lesson_completed": (
                    request.stage == "practice"
                    and stage_completed
                ),
                "action": (
                    "AXIS_COMPLETE"
                    if stage_completed
                    else (
                        "TARGET_COMPLETE"
                        if valid_target_completion
                        else "CONTINUE"
                    )
                ),
                "target_id": (
                    completed_target_order
                    if valid_target_completion
                    else None
                ),
                "next_target_id": next_target_order,
                "exchange_count": exchange_count_after,
            },
        )

    except Exception as exc:
        logger.exception(
            "Lesson AI stage failed: %s",
            exc,
        )

        try:
            db.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback lesson stage AI transaction."
            )

        yield sse_event(
            "error",
            {
                "message": str(exc),
            },
        )

    finally:
        db.close()


@router.post("/stage-chat")
def lesson_stage_chat(
    request: StageChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _get_lesson(
        db,
        request.lesson_id,
    )

    profile = _get_profile(
        db,
        current_user,
        lesson,
    )

    progress = _get_stage_progress(
        db,
        current_user,
        profile,
        lesson,
    )

    _ensure_stage_open(
        progress,
        request.stage,
    )

    conversation_id = (
        request.conversation_id or ""
    )

    return StreamingResponse(
        _stream_stage_response(
            request=request,
            user_id=current_user.id,
            profile_id=profile.id,
            lesson_id=lesson.id,
            conversation_id=conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )