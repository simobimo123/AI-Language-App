from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
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
from services.ai.provider import AI_MODEL, provider
from services.ai.usage import record_api_usage
from routers.auth import get_current_user
from services.ai.conversation import (
    get_conversation_history,
    save_conversation_message,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/lesson", tags=["Lesson AI"])

MAX_STAGE_EXCHANGES = 20
MAX_HISTORY_MESSAGES = 40
MAX_HISTORY_CHARS_PER_MESSAGE = 1800
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 420


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=120)


def sse_event(event: str, data: dict) -> str:
    import json

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


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
            learn_status="locked",
            teaching_status="locked",
            practice_status="locked",
        )
        db.add(progress)
        db.flush()
    return progress


def _ensure_stage_open(progress: UserLessonStageProgress, stage: str) -> None:
    current = getattr(progress, f"{stage}_status")
    if current == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage '{stage}' is locked until the previous stage is completed.",
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
    field_name = f"{stage}_conversation_id"
    conversation_id = f"lesson_{stage}_{uuid4()}"
    setattr(progress, field_name, conversation_id)
    return conversation_id


def _get_canonical_conversation_id(
    progress: UserLessonStageProgress,
    stage: str,
) -> str:
    field_name = f"{stage}_conversation_id"
    prefix = f"lesson_{stage}_"
    current = str(getattr(progress, field_name, "") or "").strip()
    if current and current.startswith(prefix):
        return current
    return _new_stage_conversation_id(progress, stage)


def _targets(db: Session, lesson_id: int) -> list[dict]:
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
                "patterns": [pattern.pattern for pattern in patterns[:2]],
                "required": row.required,
            }
        )
    return result


def _practice_context(db: Session, lesson_id: int) -> dict | None:
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


def _history_messages(history) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = "assistant" if item.role == "model" else item.role
        if role not in {"user", "assistant"}:
            continue
        content = str(item.content or "").strip()
        if not content:
            continue
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE].rstrip() + "…"
        result.append({"role": role, "content": content})
    return result


def _exchange_count(history) -> int:
    return sum(1 for item in history if item.role == "user")


def _compact_goals(targets: list[dict]) -> str:
    lines: list[str] = []
    for target in targets:
        if not target["required"]:
            continue
        goal = str(target["goal"] or "").strip()
        patterns = [str(item).strip() for item in target["patterns"] if str(item).strip()]
        if not goal and not patterns:
            continue
        order = target.get("order")
        prefix = f"{order}. " if order is not None else "- "
        if patterns:
            lines.append(f"{prefix}{goal} | {' | '.join(patterns)}" if goal else f"{prefix}{' | '.join(patterns)}")
        else:
            lines.append(f"{prefix}{goal}")
    return "\n".join(lines) or "- Follow the lesson objectives."


def _prompt_context(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
) -> str:
    context = f"Language: {lesson.language}\nLevel: {lesson.level}\nTeaching targets:\n{_compact_goals(targets)}"
    if scenario:
        context += (
            f"\nScenario: {scenario.get('title', '')}. {scenario.get('context', '')}. "
            f"{scenario.get('instructions', '')}"
        )
    return context


def _teaching_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    is_start: bool,
) -> str:
    start_rule = (
        " First reply: speak directly to the learner in one natural message."
        if is_start
        else ""
    )
    return f"""You are the teaching tutor.
{_prompt_context(lesson=lesson, targets=targets, scenario=None)}
Teach the targets one at a time, in order.
Use short, level-appropriate language.
Give one short explanation, example, task, or question for the current target, then wait for the learner's response.
Never speak for the learner, predict their answer, or answer your own question.
Output only natural words intended for the learner. Never output lesson metadata, headings, labels, plans, internal instructions, or unresolved placeholders such as {{name}}, {{word}}, or {{answer}}.
Understand the learner's intended meaning, even when the answer is incomplete or very short.
If meaningful but incomplete, give the natural complete form and ask the learner to repeat it.
Do not merely repeat the same request.
Check the answer before moving to the next target.
If correct, give brief feedback and continue.
If incorrect, briefly correct the error and ask for another attempt.
Use the learner's native language only for brief explanations or corrections when needed.
Never invent learner responses. Reply only as the tutor.{start_rule}""".strip()


def _practice_system_prompt(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    start_rule = (
        " First reply: one short natural message ending with one question."
        if is_start
        else ""
    )
    return f"""You are the practice conversation partner.
{_prompt_context(lesson=lesson, targets=targets, scenario=scenario)}
Have a natural conversation using the lesson targets.
Use one target at a time, in order when practical.
Ask one question at a time and wait for the learner's answer.
Never speak for the learner or answer your own questions.
Do not invent learner responses.
Output only natural words intended for the learner. Never output lesson metadata, headings, labels, plans, internal instructions, or unresolved placeholders such as {{name}} or {{word}}.
Understand the learner's intended meaning, even when the answer is incomplete or very short.
When correction is needed, briefly give the natural form and continue the conversation; do not merely repeat the same request.
Keep language short and level-appropriate.
Correct only important mistakes briefly.
Do not turn the conversation into a formal lesson or worksheet.
Reply only as the conversation partner.{start_rule}""".strip()


def _system_prompt(
    *,
    stage: str,
    lesson: CourseLesson,
    user: User,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    """Select the independent prompt for the current AI agent."""
    if stage == "teaching":
        return _teaching_system_prompt(
            lesson=lesson,
            targets=targets,
            is_start=is_start,
        )
    return _practice_system_prompt(
        lesson=lesson,
        targets=targets,
        scenario=scenario,
        is_start=is_start,
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
            raise RuntimeError("User not found.")

        lesson = _get_lesson(db, lesson_id)
        profile = db.get(LearningProfile, profile_id)
        if profile is None:
            raise RuntimeError("Learning profile not found.")

        stage_progress = _get_stage_progress(db, user, profile, lesson)
        _ensure_stage_open(stage_progress, request.stage)

        is_control_message = request.message == "START_STAGE"

        # START_STAGE always begins a clean AI session. Reusing an old
        # conversation here makes the tutor sound as if the learner already
        # spoke before opening the page and also wastes input tokens on stale history.
        if is_control_message:
            conversation_id = _new_stage_conversation_id(stage_progress, request.stage)
            history = []
        else:
            canonical_conversation_id = _get_canonical_conversation_id(
                stage_progress, request.stage
            )
            if canonical_conversation_id != conversation_id:
                conversation_id = canonical_conversation_id
            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=40,
                db=db,
            )

        if request.stage == "teaching" and stage_progress.learn_status != "completed":
            raise RuntimeError("Teaching requires completed interactive learning.")
        if request.stage == "practice" and stage_progress.teaching_status != "completed":
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        if not any(target["required"] for target in targets):
            raise RuntimeError("Lesson has no required training targets.")

        exchange_count_before = _exchange_count(history)

        if exchange_count_before >= MAX_STAGE_EXCHANGES and not is_control_message:
            _complete_stage(
                stage_progress=stage_progress,
                stage=request.stage,
                conversation_id=conversation_id,
            )
            db.commit()
            yield sse_event(
                "done",
                {
                    "conversation_id": conversation_id,
                    "stage": request.stage,
                    "axis_completed": True,
                    "lesson_completed": request.stage == "practice",
                    "action": "AXIS_COMPLETE",
                },
            )
            return

        messages = _history_messages(history)
        learner_message = request.message[:MAX_LEARNER_MESSAGE_CHARS]
        if not is_control_message:
            messages.append({"role": "user", "content": learner_message})

        scenario = _practice_context(db, lesson.id) if request.stage == "practice" else None

        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=_system_prompt(
                stage=request.stage,
                lesson=lesson,
                user=user,
                targets=targets,
                scenario=scenario,
                is_start=is_control_message,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        reply = str(response.text or "").strip()
        if not reply:
            raise RuntimeError("AI tutor returned an empty response.")

        if not is_control_message:
            exchange_count_after = exchange_count_before + 1
            save_conversation_message(user.id, conversation_id, "user", request.message, db)
        else:
            exchange_count_after = exchange_count_before

        save_conversation_message(user.id, conversation_id, "assistant", reply, db)

        axis_completed = not is_control_message and exchange_count_after >= MAX_STAGE_EXCHANGES
        if axis_completed:
            _complete_stage(
                stage_progress=stage_progress,
                stage=request.stage,
                conversation_id=conversation_id,
            )

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
            logger.exception("Failed to record lesson AI usage.")

        yield sse_event("conversation", {"conversation_id": conversation_id})
        yield sse_event("token", {"text": reply})
        yield sse_event(
            "decision",
            {
                "action": "AXIS_COMPLETE" if axis_completed else "CONTINUE",
                "target_id": None,
                "confidence": None,
            },
        )
        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "stage": request.stage,
                "axis_completed": axis_completed,
                "lesson_completed": request.stage == "practice" and axis_completed,
                "action": "AXIS_COMPLETE" if axis_completed else "CONTINUE",
                "exchange_count": exchange_count_after,
                "max_exchanges": MAX_STAGE_EXCHANGES,
            },
        )
    except Exception as exc:
        logger.exception("Lesson AI stage failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback lesson stage AI transaction.")
        yield sse_event("error", {"message": str(exc)})
    finally:
        db.close()


@router.post("/stage-chat")
def stage_chat(
    request: StageChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _get_lesson(db, request.lesson_id)

    profile = db.scalar(
        select(LearningProfile).where(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == lesson.language,
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learning profile not found for this lesson language.",
        )

    progress = _get_stage_progress(db, current_user, profile, lesson)
    _ensure_stage_open(progress, request.stage)

    is_control_message = request.message == "START_STAGE"
    if is_control_message:
        conversation_id = _new_stage_conversation_id(progress, request.stage)
        db.commit()
    else:
        conversation_id = _get_canonical_conversation_id(progress, request.stage)
        db.commit()

    from fastapi.responses import StreamingResponse

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
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
