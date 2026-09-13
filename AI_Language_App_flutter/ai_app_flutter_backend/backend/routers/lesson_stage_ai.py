from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
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


# ============================================================
# AI CONTEXT / OUTPUT LIMITS
# ============================================================
# Maximum amount of lesson history kept/retrieved from RAM.
# This is also used for completion-marker analysis.
MAX_HISTORY_MESSAGES = 40
# Teaching needs one previous exchange; Practice keeps two.
# Full history remains available for progress analysis.
MAX_TEACHING_CONTEXT_MESSAGES = 2
MAX_PRACTICE_CONTEXT_MESSAGES = 4
# Maximum characters from each message sent to the AI.
MAX_HISTORY_CHARS_PER_MESSAGE = 1400
# Maximum learner message size accepted/sent to the AI.
MAX_LEARNER_MESSAGE_CHARS = 800
# Maximum AI output size.
MAX_OUTPUT_TOKENS = 420


# ============================================================
# INTERNAL CONTROL MARKERS
# ============================================================
TARGET_COMPLETE_PATTERN = re.compile(
    r"\[\[TARGET_COMPLETE:(\d+)\]\]",
    re.IGNORECASE,
)
TEACHING_COMPLETE_PATTERN = re.compile(
    r"\[\[TEACHING_COMPLETE\]\]",
    re.IGNORECASE,
)


# ============================================================
# REQUEST MODEL
# ============================================================
class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )


# ============================================================
# SSE
# ============================================================
def sse_event(event: str, data: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


# ============================================================
# DATABASE HELPERS
# ============================================================
def _get_lesson(
    db: Session,
    lesson_id: int,
) -> CourseLesson:
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
    current = getattr(
        progress,
        f"{stage}_status",
    )
    if current == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Stage '{stage}' is locked until the previous "
                "stage is completed."
            ),
        )
    # A completed stage may be opened again for review.
    #
    # Important:
    # - The completed status is preserved.
    # - START_STAGE creates a new conversation ID.
    # - Existing lesson progress is not reset.
    # - Practice remains governed by its own existing rules.


# ============================================================
# CONVERSATION IDs
# ============================================================
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


# ============================================================
# LESSON TARGETS
# ============================================================
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
            .where(
                LessonTargetPattern.target_id == row.id
            )
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
                "success_criteria": getattr(
                    row,
                    "success_criteria",
                    "",
                ),
            }
        )
    return result


def _practice_context(
    db: Session,
    lesson_id: int,
) -> dict | None:
    row = db.scalar(
        select(LessonPracticeScenario)
        .where(
            LessonPracticeScenario.lesson_id == lesson_id
        )
        .order_by(LessonPracticeScenario.scenario_order)
    )
    if row is None:
        return None
    return {
        "title": str(
            row.title or ""
        ).strip()[:120],
        "context": str(
            row.context or ""
        ).strip()[:300],
        "instructions": str(
            row.instructions or ""
        ).strip()[:300],
    }


# ============================================================
# CONTROL MARKER CLEANUP
# ============================================================
def _remove_control_markers(text: str) -> str:
    cleaned = TARGET_COMPLETE_PATTERN.sub(
        "",
        text,
    )
    cleaned = TEACHING_COMPLETE_PATTERN.sub(
        "",
        cleaned,
    )
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


# ============================================================
# HISTORY
# ============================================================
def _history_messages(
    history,
    max_messages: int,
) -> list[dict[str, str]]:
    """
    Convert lesson history into the small recent context
    actually sent to the AI.

    The full lesson history remains available in RAM and is
    still used for target-completion marker analysis.

    Teaching sends one previous exchange; Practice sends two.
    """
    result: list[dict[str, str]] = []
    for item in history[-max_messages:]:
        role = (
            "assistant"
            if item.role == "model"
            else item.role
        )
        if role not in {"user", "assistant"}:
            continue
        content = str(
            item.content or ""
        ).strip()
        if not content:
            continue
        content = _remove_control_markers(content)
        if not content:
            continue
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = (
                content[
                    :MAX_HISTORY_CHARS_PER_MESSAGE
                ].rstrip()
                + "…"
            )
        result.append(
            {
                "role": role,
                "content": content,
            }
        )
    return result


# ============================================================
# TARGET PROGRESS
# ============================================================
def _completed_target_orders(
    history,
) -> list[int]:
    completed: set[int] = set()
    for item in history:
        if item.role not in {"assistant", "model"}:
            continue
        content = str(
            item.content or ""
        )
        for match in TARGET_COMPLETE_PATTERN.finditer(
            content
        ):
            try:
                target_order = int(
                    match.group(1)
                )
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
    return required_orders.issubset(
        completed_orders
    )


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


# ============================================================
# COMPACT TARGET SUMMARY
# ============================================================
def _compact_target_goals(
    targets: list[dict],
) -> str:
    """
    Compact lesson objective summary used by Practice AI.
    Practice does not need every target pattern and success
    criterion. It only needs to know what the lesson is
    trying to practice.
    """
    lines: list[str] = []
    for target in targets:
        if not target["required"]:
            continue
        goal = str(
            target["goal"] or ""
        ).strip()
        if not goal:
            continue
        prefix = (
            f"{target.get('order')}. "
            if target.get("order") is not None
            else "- "
        )
        lines.append(
            f"{prefix}{goal}"
        )
    return (
        "\n".join(lines)
        or "- Follow the lesson objectives."
    )


# ============================================================
# PROMPT CONTEXT
# ============================================================
def _prompt_context(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None = None,
    include_target_summary: bool = False,
) -> str:
    """
    Build only the context required by the current AI stage.
    Teaching:
        language + level
        current target is added separately with full detail.
    Practice:
        language + level
        compact lesson target summary
        practice scenario
    """
    context = (
        f"**LANGUAGE**: {lesson.language}\n"
        f"**LEVEL**: {lesson.level}"
    )
    if include_target_summary:
        context += (
            "\n"
            "\n"
            f"**LESSON TARGETS**:\n"
            f"{_compact_target_goals(targets)}"
        )
    if scenario:
        context += (
            "\n\n"
            f"**PRACTICE SCENARIO**: "
            f"{scenario.get('title', '')}\n"
            f"{scenario.get('context', '')}\n"
            f"{scenario.get('instructions', '')}"
        )
    return context


# ============================================================
# TEACHING AI
# ============================================================
def _teaching_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    current_target_order: int | None,
    is_start: bool,
) -> str:
    current_target = _target_by_order(targets, current_target_order)
    if current_target is None:
        current_target_text = "**CURRENT TARGET**: There is no remaining target."
    else:
        goal = str(current_target.get("goal", "")).strip()
        patterns = [str(item).strip() for item in current_target.get("patterns", []) if str(item).strip()]
        success_criteria = str(current_target.get("success_criteria", "")).strip()
        current_target_text = f"**CURRENT TARGET**: {goal}"
        if patterns:
            current_target_text += f"\n**TARGET PATTERNS**: {' | '.join(patterns)}"
        if success_criteria:
            current_target_text += f"\n**SUCCESS CRITERIA**: {success_criteria}"
    task = (
        "**START**: Briefly introduce the target, then ask the learner to produce it."
        if is_start
        else "**RESPONSE**: Judge the learner's answer against the target and success criteria. "
             "If not met, stay on the same target. For meaningful errors, briefly correct/model "
             "and ask for another attempt. Do not declare success early."
    )
    return f"""
You are the **TEACHING AI** for a {lesson.level} language lesson.

Teach the **CURRENT TARGET** through a short teacher-learner exchange. You are the teacher, not the practice partner.

{_prompt_context(lesson=lesson, targets=targets)}

{current_target_text}

**RULES**:
- Focus on the current target and its **SUCCESS CRITERIA**.
- **TARGET PATTERNS** guide teaching; they are not exact required sentences.
- Respond to what the learner actually says and let them attempt; never answer for them.
- Keep explanations brief and level-appropriate; prefer short examples/prompts.
- If incorrect or incomplete, give the smallest useful correction/model and ask for another attempt.
- Do not move on until the success criteria are clearly met.
- Accept natural alternatives that satisfy the criteria.
- Answer useful target questions briefly, then return to practice.
- Handle unrelated replies naturally and guide back to the target.
- Keep normal responses to 2-3 short sentences.

{task}

**COMPLETION**:
Only when the learner clearly meets the success criteria, give brief positive feedback and append:
[[TARGET_COMPLETE:{current_target_order}]]

The marker must be last and never be shown or explained.
""".strip()


# ============================================================
# PRACTICE AI
# ============================================================
def _practice_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    task = (
        "**START**: Begin naturally from the scenario, use one suitable target, and invite one response."
        if is_start
        else "**CONTINUE**: Respond to the learner's actual message and use it to continue naturally."
    )
    return f"""
You are the **PRACTICE AI** for a {lesson.level} language lesson.

You are a natural conversation partner, not the formal teacher.

{_prompt_context(
    lesson=lesson,
    targets=targets,
    scenario=scenario,
    include_target_summary=True,
)}

**RULES**:
- Practice lesson targets naturally, preferably one at a time; never force a checklist.
- Respond to the learner's actual message and let them drive; never speak or invent an answer for them.
- Ask at most one natural question at a time and give room to answer.
- Follow interesting answers naturally; every question needs a reason.
- If the learner asks you something, answer naturally and continue.
- Correct only meaningful errors, briefly; minor errors need not stop the conversation.
- Keep language level-appropriate, short, and natural.
- Do not make it a grammar lesson or formal exercise.
- Output only learner-facing conversation: no metadata, labels, placeholders, markers, or instructions.

{task}
""".strip()


# ============================================================
# SYSTEM PROMPT SELECTOR
# ============================================================
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


# ============================================================
# AI RESPONSE / MARKERS
# ============================================================
def _extract_target_completion(
    reply: str,
) -> tuple[str, int | None, bool]:
    target_match = TARGET_COMPLETE_PATTERN.search(
        reply
    )
    teaching_complete = bool(
        TEACHING_COMPLETE_PATTERN.search(
            reply
        )
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


# ============================================================
# STAGE COMPLETION
# ============================================================
def _complete_stage(
    *,
    stage_progress: UserLessonStageProgress,
    stage: str,
    conversation_id: str,
) -> None:
    now = datetime.now(timezone.utc)
    if stage == "teaching":
        stage_progress.teaching_status = "completed"
        stage_progress.teaching_completed_at = now
        stage_progress.teaching_conversation_id = (
            conversation_id
        )
        if stage_progress.practice_status == "locked":
            stage_progress.practice_status = "available"
    else:
        stage_progress.practice_status = "completed"
        stage_progress.practice_completed_at = now
        stage_progress.practice_conversation_id = (
            conversation_id
        )


# ============================================================
# STREAM STAGE RESPONSE
# ============================================================
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
        user = db.get(
            User,
            user_id,
        )
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
            conversation_id = (
                _new_stage_conversation_id(
                    stage_progress,
                    request.stage,
                )
            )
            history = []
        else:
            canonical_conversation_id = (
                _get_canonical_conversation_id(
                    stage_progress,
                    request.stage,
                )
            )
            if (
                canonical_conversation_id
                != conversation_id
            ):
                conversation_id = (
                    canonical_conversation_id
                )
            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=MAX_HISTORY_MESSAGES,
                db=db,
            )
        if (
            request.stage == "practice"
            and stage_progress.teaching_status
            != "completed"
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
            current_target_order = (
                _current_target_order(
                    targets,
                    history,
                )
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
        # Full history remains available above for progress and
        # completion-marker analysis. Only compact recent history
        # is sent to the AI.
        context_message_limit = (
            MAX_TEACHING_CONTEXT_MESSAGES
            if request.stage == "teaching"
            else MAX_PRACTICE_CONTEXT_MESSAGES
        )
        messages = _history_messages(
            history,
            context_message_limit,
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
        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=_system_prompt(
                stage=request.stage,
                lesson=lesson,
                targets=targets,
                scenario=scenario,
                current_target_order=current_target_order,
                is_start=is_control_message,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        raw_reply = str(
            response.text or ""
        ).strip()
        if not raw_reply:
            raise RuntimeError(
                "AI tutor returned an empty response."
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
        # ====================================================
        # BACKEND SAFEGUARD
        # ====================================================
        valid_target_completion = False
        if (
            request.stage == "teaching"
            and completed_target_order is not None
            and current_target_order is not None
            and completed_target_order
            == current_target_order
            and not is_control_message
        ):
            valid_target_completion = True
        # ====================================================
        # SAVE USER MESSAGE
        # ====================================================
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
        # ====================================================
        # ADD BACKEND CONTROL MARKERS
        # ====================================================
        stored_assistant_reply = reply
        if valid_target_completion:
            stored_assistant_reply = (
                f"{reply}\n"
                f"[[TARGET_COMPLETE:"
                f"{completed_target_order}"
                f"]]"
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
        # ====================================================
        # SAVE ASSISTANT MESSAGE
        # ====================================================
        save_conversation_message(
            user.id,
            conversation_id,
            "assistant",
            stored_assistant_reply,
            db,
        )
        # ====================================================
        # COMPLETE STAGE
        # ====================================================
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
        # ====================================================
        # RECORD AI USAGE
        # ====================================================
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
        # ====================================================
        # NEXT TARGET
        # ====================================================
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
        # ====================================================
        # SSE: CONVERSATION
        # ====================================================
        yield sse_event(
            "conversation",
            {
                "conversation_id": conversation_id,
            },
        )
        # ====================================================
        # SSE: TOKEN
        # ====================================================
        yield sse_event(
            "token",
            {
                "text": reply,
            },
        )
        # ====================================================
        # SSE: DECISION
        # ====================================================
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
                    "next_target_id": (
                        next_target_order
                    ),
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
        # ====================================================
        # SSE: DONE
        # ====================================================
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


# ============================================================
# API ROUTE
# ============================================================
@router.post("/stage-chat")
def lesson_stage_chat(
    request: StageChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
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
