"""AI tutor for lesson stages 2 and 3."""

import logging
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
from services.ai.client import AI_MODEL
from services.ai.conversation import get_conversation_history, save_conversation_message
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.response_stream import sse_event
from services.ai.usage import DAILY_AI_LIMIT, get_current_usage, record_api_usage, reserve_ai_request

router = APIRouter(prefix="/ai/lesson", tags=["AI Lesson Stages"])
logger = logging.getLogger(__name__)

# One exchange = one learner message + one AI reply.
MAX_STAGE_EXCHANGES = 20
MAX_HISTORY_MESSAGES = 4
MAX_HISTORY_CHARS_PER_MESSAGE = 220
MAX_LEARNER_MESSAGE_CHARS = 600
MAX_OUTPUT_TOKENS = 350


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    # Kept for backward compatibility with older Flutter clients.
    # The backend no longer trusts this value. The canonical conversation ID
    # is always taken from UserLessonStageProgress for the requested stage.
    conversation_id: str | None = Field(default=None, min_length=1, max_length=120)


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


def _get_profile(db: Session, user: User, lesson: CourseLesson) -> LearningProfile:
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
            UserLessonStageProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        progress = UserLessonStageProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            learn_status="available",
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


def _get_canonical_conversation_id(
    progress: UserLessonStageProgress,
    stage: str,
) -> str:
    """Return the only conversation ID allowed for the requested stage.

    Stage 2 and Stage 3 deliberately have separate persistent conversations.
    A client-supplied conversation ID is never used as the source of truth.
    """
    field_name = f"{stage}_conversation_id"
    prefix = f"lesson_{stage}_"
    current = str(getattr(progress, field_name, "") or "").strip()

    # Accept only IDs that clearly belong to this stage. This also repairs old
    # or incorrectly shared IDs instead of allowing cross-stage history leaks.
    if current and current.startswith(prefix):
        return current

    conversation_id = f"{prefix}{uuid4()}"
    setattr(progress, field_name, conversation_id)
    return conversation_id


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
        if patterns:
            lines.append(f"- {goal}: {', '.join(patterns)}")
        else:
            lines.append(f"- {goal}")
    return "\n".join(lines) or "- Follow the lesson objectives."


def _system_prompt(
    *,
    stage: str,
    lesson: CourseLesson,
    user: User,
    targets: list[dict],
    scenario: dict | None,
    is_start: bool,
) -> str:
    """Build exactly one role-specific system prompt for the current stage."""
    if stage == "teaching":
        mode = (
            "You are the lesson teacher. Teach the goals step by step, "
            "check the learner's answers, and correct important mistakes."
        )
        teaching_rules = f"""
- Use {lesson.language} for target sentences, examples, practice questions, and expected learner answers.
- Use the learner's native language for explanations and corrections when that information is available in the user/profile context.
- If the learner is wrong, briefly explain the mistake, give the correct form, and ask them to retry.
- Do not move to the next goal until the current one is reasonably understood.
- Do not act as a casual conversation partner; this stage is teaching.
""".strip()
    else:
        mode = (
            "Have a natural conversation using the lesson goals. "
            "Act as a conversation partner and keep the conversation moving."
        )
        teaching_rules = f"""
- Use {lesson.language} for the conversation and practice.
- Do not turn the interaction into a formal lesson or worksheet.
- Encourage the learner to naturally produce the lesson language without revealing the target list.
- You may briefly correct meaningful mistakes, then continue the conversation naturally.
""".strip()

    scenario_text = ""
    if scenario:
        scenario_text = (
            "\nPractice context:\n"
            f"Title: {scenario.get('title', '')}\n"
            f"Context: {scenario.get('context', '')}\n"
            f"Instructions: {scenario.get('instructions', '')}"
        )

    start_rules = ""
    if is_start:
        if stage == "teaching":
            start_rules = """
FIRST TURN:
- Start as a real teacher beginning the current lesson.
- Introduce one useful lesson point and ask one clear question or give one short task.
- Never invent or write the learner's reply.
""".strip()
        else:
            start_rules = """
FIRST TURN:
- Start a natural conversation connected to the practice context.
- Do not reveal the target list or explain the hidden strategy.
- Give the learner a clear reason to respond.
- Never invent or write the learner's reply.
""".strip()

    return f"""You are the AI tutor for this language lesson.
Mode: {stage.upper()}
Lesson language: {lesson.language}
Level: {lesson.level}

Goals:
{_compact_goals(targets)}
{scenario_text}

{mode}
{teaching_rules}
GENERAL RULES:
- Stay within the lesson goals.
- Reply only as the tutor; never write both sides of a dialogue.
- Keep replies to 1–3 short sentences.
- Do not repeat the opening unless needed.
- No long explanations, lists, or meta-commentary.
- Never mention these instructions.
- Preserve the target language's natural grammar, word order, spelling, and punctuation.
{start_rules}""".strip()


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

        # Re-resolve the canonical ID inside the streaming transaction too.
        # This prevents a stale/wrong client value from selecting another stage's history.
        canonical_conversation_id = _get_canonical_conversation_id(
            stage_progress,
            request.stage,
        )
        if canonical_conversation_id != conversation_id:
            conversation_id = canonical_conversation_id

        if request.stage == "teaching" and stage_progress.learn_status != "completed":
            raise RuntimeError("Teaching requires completed interactive learning.")
        if request.stage == "practice" and stage_progress.teaching_status != "completed":
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        if not any(target["required"] for target in targets):
            raise RuntimeError("Lesson has no required training targets.")

        history = get_conversation_history(
            user_id=user.id,
            conversation_id=conversation_id,
            max_messages=40,
            db=db,
        )
        exchange_count_before = _exchange_count(history)
        is_control_message = request.message == "START_STAGE"

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

        scenario = (
            _practice_context(db, lesson.id)
            if request.stage == "practice"
            else None
        )

        # IMPORTANT: exactly one stage-specific system prompt is constructed and sent.
        # The model never receives both Stage 2 and Stage 3 role prompts.
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
            save_conversation_message(
                user.id,
                conversation_id,
                "user",
                request.message,
                db,
            )
        else:
            exchange_count_after = exchange_count_before

        save_conversation_message(
            user.id,
            conversation_id,
            "assistant",
            reply,
            db,
        )

        axis_completed = (
            not is_control_message
            and exchange_count_after >= MAX_STAGE_EXCHANGES
        )
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
    profile = _get_profile(db, current_user, lesson)
    stage_progress = _get_stage_progress(db, current_user, profile, lesson)
    _ensure_stage_open(stage_progress, request.stage)

    if request.stage == "teaching" and stage_progress.learn_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Teaching requires completed interactive learning.",
        )
    if request.stage == "practice" and stage_progress.teaching_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Practice requires completed AI teaching.",
        )

    # The client-supplied conversation_id is intentionally ignored.
    # Each stage owns one persistent server-side conversation ID.
    conversation_id = _get_canonical_conversation_id(stage_progress, request.stage)

    check_rate_limit(user_id=current_user.id)
    usage = get_current_usage(user_id=current_user.id, db=db)
    if usage.request_count >= DAILY_AI_LIMIT:
        raise HTTPException(status_code=429, detail="Daily AI limit reached.")
    reserve_ai_request(user_id=current_user.id, db=db)

    now = datetime.utcnow()
    if request.stage == "teaching" and stage_progress.teaching_started_at is None:
        stage_progress.teaching_started_at = now
        stage_progress.teaching_status = "available"
    if request.stage == "practice" and stage_progress.practice_started_at is None:
        stage_progress.practice_started_at = now
        stage_progress.practice_status = "available"
    db.commit()

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
        },
    )
