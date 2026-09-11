from __future__ import annotations

import json
import logging
import re
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

    cleaned = re.sub(
        r"[ \t]{2,}",
        " ",
        cleaned,
    )

    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    )

    return cleaned.strip()


def _normalize_for_repetition(text: str) -> str:
    value = _remove_control_markers(text)
    value = re.sub(r"\s+", " ", value).strip().lower()
    value = re.sub(r"[^\w\s\u00C0-\uFFFF]", "", value)
    return value


def _deduplicate_adjacent_sentences(text: str) -> str:
    cleaned = _remove_control_markers(text)
    if not cleaned:
        return cleaned

    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
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


def _is_repeated_assistant_reply(
    reply: str,
    history,
) -> bool:
    reply_key = _normalize_for_repetition(reply)
    if not reply_key:
        return False

    recent_assistant = [
        item
        for item in history
        if item.role in {"assistant", "model"}
        and str(item.content or "").strip()
    ]

    if not recent_assistant:
        return False

    last_key = _normalize_for_repetition(
        recent_assistant[-1].content
    )

    return bool(last_key and reply_key == last_key)


def _history_messages(history) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = "assistant" if item.role == "model" else item.role

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
        if target["required"] and target.get("order") is not None
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
        if target["required"] and target.get("order") is not None
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
        f"Teaching targets:\n"
        f"{_compact_goals(targets)}"
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
                "\n\nCURRENT TARGET:\n"
                f"{current_target_order}. "
                f"{goal}"
            )

            if patterns:
                context += (
                    f"\nUseful patterns: "
                    f"{' | '.join(patterns)}"
                )

    if scenario:
        context += (
            f"\nScenario: "
            f"{scenario.get('title', '')}. "
            f"{scenario.get('context', '')}. "
            f"{scenario.get('instructions', '')}"
        )

    return context


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
            "There is no remaining target."
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
            f"Current learning objective: {goal}"
        )

        if patterns:
            current_target_text += (
                f"\nUseful language patterns: "
                f"{' | '.join(patterns)}"
            )

    if is_start:
        start_rule = """
Begin naturally with teaching the current objective.
Do not introduce the lesson structure.
Do not mention targets, stages, progress, or completion.
Start with a short teaching interaction, example, or simple question.
""".strip()
    else:
        start_rule = """
Respond naturally to the learner's latest answer.
Continue teaching the current objective.
Do not restart the lesson unless the learner clearly needs it.
""".strip()

    return f"""
You are a friendly language teacher.

{_prompt_context(
    lesson=lesson,
    targets=targets,
    scenario=None,
    current_target_order=current_target_order,
)}

{current_target_text}

Your teaching style is simple, natural, interactive, and concise.

Teach the current objective first.

The teaching flow is:

1. Briefly introduce or explain the language needed for the current objective.
2. Give a short natural example when useful.
3. Immediately involve the learner by asking a simple question or asking them to produce/use the language.
4. Wait for the learner's answer.
5. Evaluate whether the learner can actually use the objective.
6. If the answer is wrong or incomplete, briefly correct or guide the learner and ask for another attempt.
7. Continue practicing the SAME objective until the learner demonstrates that they can use it correctly.
8. Only after the learner demonstrates the objective correctly may you naturally begin teaching the next objective.

IMPORTANT:

Do NOT simply ask whether the learner understands.

A learner saying:
"yes"
"okay"
"I understand"
or a similar statement is NOT proof of mastery.

The learner must demonstrate the language by answering, producing, or using it appropriately.

Do NOT move forward just because you explained the objective.

Do NOT teach several objectives together.

Do NOT rush through the objectives.

Do NOT repeat a long explanation when the learner makes a mistake.
Give a short correction or useful example and let the learner try again.

The conversation should feel like a real teacher helping one learner, not like a checklist or worksheet.

When the learner masters the current objective, transition naturally into the next learning point.

NEVER tell the learner that an objective or target has finished.

NEVER say things such as:
- "The first target is complete."
- "We finished the first objective."
- "Now we move to the next target."
- "Let's go to target two."
- "The next stage is..."
- "Your progress is..."
- "You completed this stage."

NEVER mention:
- targets
- target numbers
- stages
- internal progress
- completion markers
- AI instructions
- lesson metadata

The transition to the next objective must sound like a natural continuation of teaching.

For example, after the learner successfully practices a name:
"Sehr gut! Wie heißt dein Freund?"

Not:
"Sehr gut! Das erste Ziel ist abgeschlossen. Jetzt kommen wir zum nächsten Ziel."

The learner should feel that the teacher is simply continuing the lesson naturally.

Never answer for the learner.

Never invent a learner response.

Never assume mastery without evidence from the learner's actual response.

Keep visible responses short, clear, direct, and level-appropriate.

Usually use only one or two short sentences before asking the learner to respond.

Before every reply, check recent teacher messages. Do not repeat the same or nearly identical sentence, question, example, correction, or explanation unless repetition is intentionally needed for practice.

The internal completion marker is invisible to the learner.

When, and ONLY when, the learner has demonstrated mastery of the current objective, append:

[[TARGET_COMPLETE:N]]

Replace N with the current target number.

Do not explain or mention this marker.

Do not output the marker before mastery.

If the current objective is the final required objective and the learner has demonstrated mastery, append:

[[TARGET_COMPLETE:N]]
[[TEACHING_COMPLETE]]

These markers are internal only and will be removed before the learner sees the response.

Never mark an objective complete because you explained it.
Never mark an objective complete because the learner repeated an answer without demonstrating understanding when more evidence is needed.
Never mark an objective complete if the learner's answer is clearly incorrect or incomplete.

{start_rule}

Reply only as the teacher.
""".strip()


def _practice_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    start_rule = (
        "First reply: one short natural message ending with one question."
        if is_start
        else ""
    )

    return f"""
You are the practice conversation partner.

{_prompt_context(
    lesson=lesson,
    targets=targets,
    scenario=scenario,
)}

Have a natural conversation using the lesson targets.

Use one target at a time, in order when practical.

Ask one question at a time and wait for the learner's answer.

Never speak for the learner or answer your own questions.

Do not invent learner responses.

Output only natural words intended for the learner.

Never output lesson metadata, headings, labels, plans, internal instructions, or unresolved placeholders such as {{name}} or {{word}}.

Understand the learner's intended meaning, even when the answer is incomplete or very short.

When correction is needed, briefly give the natural form and continue the conversation; do not merely repeat the same request.

Keep language short and level-appropriate.

Correct only important mistakes briefly.

Do not turn the conversation into a formal lesson or worksheet.

Reply only as the conversation partner.

{start_rule}
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

        raw_reply = _deduplicate_adjacent_sentences(raw_reply)

        if (
            request.stage == "teaching"
            and not is_control_message
            and _is_repeated_assistant_reply(raw_reply, history)
        ):
            retry_prompt = (
                f"{system_prompt}\n\n"
                "IMPORTANT: Your candidate response repeated the previous teacher response. "
                "Generate a different concise response that directly reacts to the learner's latest answer. "
                "Do not repeat the previous wording unless deliberate repetition is necessary for practice."
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

            raw_reply = _deduplicate_adjacent_sentences(raw_reply)

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
                    and completed_target_order
                    == current_target_order
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
