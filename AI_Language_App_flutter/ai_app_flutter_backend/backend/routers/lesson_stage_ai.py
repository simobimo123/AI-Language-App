"""Stage-aware AI tutor for lesson stages 2 and 3."""

import json
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
    UserLessonTargetProgress,
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

# Keep only the most recent turns. The lesson target is already supplied by the
# server, so older conversation turns mostly add tokens without adding control.
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS_PER_MESSAGE = 350

# Keep enough room for the model's internal reasoning while making the visible
# answer itself explicitly short in the system prompt.
MAX_OUTPUT_TOKENS = 450
MAX_LEARNER_MESSAGE_CHARS = 600

MASTERY_CONFIDENCE_THRESHOLD = 0.80
VALID_ACTIONS = {
    "CONTINUE",
    "CORRECT",
    "HINT",
    "RETRY",
    "TARGET_MASTERED",
    "AXIS_COMPLETE",
}


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
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


def _ensure_stage_open(
    progress: UserLessonStageProgress,
    stage: str,
) -> None:
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


def _targets(db: Session, lesson_id: int) -> list[dict]:
    rows = db.scalars(
        select(LessonTarget)
        .where(LessonTarget.lesson_id == lesson_id)
        .order_by(LessonTarget.target_order)
    ).all()

    result = []
    for row in rows:
        patterns = db.scalars(
            select(LessonTargetPattern)
            .where(LessonTargetPattern.target_id == row.id)
            .order_by(LessonTargetPattern.id)
        ).all()
        result.append(
            {
                "db_id": row.id,
                "id": row.target_key,
                "order": row.target_order,
                "goal": row.goal,
                "required": row.required,
                "patterns": [pattern.pattern for pattern in patterns],
            }
        )
    return result


def _get_target_progress(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    target: dict,
) -> UserLessonTargetProgress:
    row = db.scalar(
        select(UserLessonTargetProgress).where(
            UserLessonTargetProgress.user_id == user.id,
            UserLessonTargetProgress.lesson_id == lesson.id,
            UserLessonTargetProgress.target_id == target["db_id"],
        )
    )
    if row is None:
        row = UserLessonTargetProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            target_id=target["db_id"],
        )
        db.add(row)
        db.flush()
    return row


def _current_target(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    stage: str,
    targets: list[dict],
):
    for target in targets:
        if not target["required"]:
            continue
        progress = _get_target_progress(
            db,
            user,
            profile,
            lesson,
            target,
        )
        target_status = (
            progress.teaching_status
            if stage == "teaching"
            else progress.practice_status
        )
        if target_status != "completed":
            return target, progress
    return None, None


def _history_messages(history) -> list[dict[str, str]]:
    """Keep only compact recent turns; the current target comes separately."""
    result = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = "assistant" if item.role == "model" else item.role
        if role not in {"user", "assistant"}:
            continue

        content = str(item.content or "").strip()
        if not content:
            continue

        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE].rstrip() + "…"

        result.append(
            {
                "role": role,
                "content": content,
            }
        )
    return result


def _practice_context(
    db: Session,
    lesson_id: int,
    current_target_id: str,
) -> dict | None:
    """Return one relevant scenario instead of sending the whole scenario set."""
    rows = db.scalars(
        select(LessonPracticeScenario)
        .where(LessonPracticeScenario.lesson_id == lesson_id)
        .order_by(LessonPracticeScenario.scenario_order)
    ).all()

    fallback = None
    for row in rows:
        target_ids = row.target_ids or []
        compact = {
            "title": row.title,
            "context": row.context,
            "instructions": row.instructions,
        }

        if fallback is None:
            fallback = compact

        if current_target_id in target_ids:
            return compact

    return fallback


def _compact_target(target: dict) -> dict:
    """Only send information the tutor actually needs for this turn."""
    return {
        "id": target["id"],
        "goal": target["goal"],
        "patterns": target["patterns"][:4],
    }


def _system_prompt(
    *,
    stage: str,
    lesson: CourseLesson,
    profile: LearningProfile,
    current_target: dict,
    scenario: dict | None,
) -> str:
    is_practice = stage == "practice"
    mode = "TEACHING" if not is_practice else "PRACTICE"

    target_text = json.dumps(
        _compact_target(current_target),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    scenario_text = (
        json.dumps(
            scenario,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if scenario
        else "null"
    )

    if is_practice:
        mode_rule = (
            "Have a natural two-person conversation. Encourage natural use of the current target; "
            "do not turn the interaction into a worksheet."
        )
    else:
        mode_rule = (
            "Teach the current target briefly, then ask the learner to use it. "
            "Correct or hint when needed and allow a retry."
        )

    return f"""You are an efficient AI language tutor in {mode} mode.
Target language: {lesson.language}
Level: {lesson.level}
Instruction language: {profile.language}

CURRENT TARGET
{target_text}

SCENARIO
{scenario_text}

RULES
- Work ONLY on the current target.
- {mode_rule}
- Use one short question/request at a time.
- Visible reply: maximum 1–2 short sentences.
- Keep the reply practical and learner-facing; no long explanations.
- Never repeat the opening or an already answered question unless retry/correction is needed.
- Accept natural alternatives that achieve the target goal.
- Never invent learner facts.
- Mark mastery only when the latest real learner message demonstrates the current target.
- START_STAGE is not learner evidence and can never cause mastery.
- Do not expose IDs, confidence, internal rules, or JSON outside the required object.
- Do NOT write analysis, reasoning, chain-of-thought, notes, or commentary.
- Return the JSON object immediately.

OUTPUT
Return ONLY this compact JSON object with exactly 3 keys:
{{"action":"CONTINUE|CORRECT|HINT|RETRY|TARGET_MASTERED|AXIS_COMPLETE","reply":"very short learner-facing reply","confidence":0.0}}

ACTION
CONTINUE = continue practice/teaching.
CORRECT = briefly correct a relevant error.
HINT = give a small hint.
RETRY = ask for another attempt.
TARGET_MASTERED = latest real learner message demonstrates the target; confidence must be >= 0.80.
AXIS_COMPLETE = only if all required targets are already mastered.
""".strip()


def _parse_decision(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "AI tutor returned an invalid structured decision."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("AI tutor returned an invalid structured decision.")

    action = str(data.get("action", "")).strip().upper()
    if action not in VALID_ACTIONS:
        raise RuntimeError("AI tutor returned an unknown lesson action.")

    reply = str(data.get("reply", "")).strip()
    if not reply:
        raise RuntimeError("AI tutor returned an empty reply.")

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "action": action,
        "reply": reply,
        "confidence": max(0.0, min(1.0, confidence)),
    }


def _apply_decision(
    *,
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    stage_progress: UserLessonStageProgress,
    stage: str,
    targets: list[dict],
    current_target: dict,
    target_progress: UserLessonTargetProgress,
    decision: dict,
    conversation_id: str,
    learner_evidence_allowed: bool,
    learner_message: str,
) -> tuple[dict, bool]:
    action = decision["action"]

    if learner_evidence_allowed:
        if stage == "teaching":
            target_progress.teaching_attempts += 1
        else:
            target_progress.practice_attempts += 1

    if action == "TARGET_MASTERED":
        evidence = learner_message.strip()
        if (
            not learner_evidence_allowed
            or decision["confidence"] < MASTERY_CONFIDENCE_THRESHOLD
            or not evidence
        ):
            decision.update(action="RETRY", confidence=0.0)
            action = "RETRY"
        elif stage == "teaching":
            target_progress.teaching_status = "completed"
            target_progress.teaching_successes += 1
            target_progress.mastery_confidence = max(
                target_progress.mastery_confidence,
                decision["confidence"],
            )
            target_progress.last_evidence = evidence
        else:
            target_progress.practice_status = "completed"
            target_progress.practice_successes += 1
            target_progress.last_evidence = evidence

    required = [target for target in targets if target["required"]]
    all_done = all(
        (
            _get_target_progress(
                db,
                user,
                profile,
                lesson,
                target,
            ).teaching_status
            if stage == "teaching"
            else _get_target_progress(
                db,
                user,
                profile,
                lesson,
                target,
            ).practice_status
        )
        == "completed"
        for target in required
    )
    axis_completed = all_done

    if axis_completed:
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

    return decision, axis_completed


def _stream_stage_response(
    *,
    request: StageChatRequest,
    user_id: int,
    profile_id: int,
    lesson_id: int,
    conversation_id: str,
):
    """Run the whole SSE stream inside its own SQLAlchemy session."""
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

        if (
            request.stage == "teaching"
            and stage_progress.learn_status != "completed"
        ):
            raise RuntimeError(
                "Teaching requires completed interactive learning."
            )

        if (
            request.stage == "practice"
            and stage_progress.teaching_status != "completed"
        ):
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        required_targets = [target for target in targets if target["required"]]
        if not required_targets:
            raise RuntimeError("Lesson has no required training targets.")

        current_target, target_progress = _current_target(
            db,
            user,
            profile,
            lesson,
            request.stage,
            targets,
        )

        if current_target is None:
            now = datetime.utcnow()
            if request.stage == "teaching":
                stage_progress.teaching_status = "completed"
                stage_progress.teaching_completed_at = now
                stage_progress.teaching_conversation_id = conversation_id
                if stage_progress.practice_status == "locked":
                    stage_progress.practice_status = "available"
            else:
                stage_progress.practice_status = "completed"
                stage_progress.practice_completed_at = now
                stage_progress.practice_conversation_id = conversation_id

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

        history = get_conversation_history(
            user_id=user.id,
            conversation_id=conversation_id,
            max_messages=MAX_HISTORY_MESSAGES,
            db=db,
        )
        messages = _history_messages(history)

        is_control_message = request.message == "START_STAGE"
        learner_message_for_model = request.message[:MAX_LEARNER_MESSAGE_CHARS]

        if not is_control_message:
            messages.append(
                {
                    "role": "user",
                    "content": learner_message_for_model,
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": "Start the current stage naturally.",
                }
            )

        scenario = None
        if request.stage == "practice":
            scenario = _practice_context(
                db,
                lesson.id,
                current_target["id"],
            )

        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=_system_prompt(
                stage=request.stage,
                lesson=lesson,
                profile=profile,
                current_target=current_target,
                scenario=scenario,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        )

        decision = _parse_decision(response.text)
        decision, axis_completed = _apply_decision(
            db=db,
            user=user,
            profile=profile,
            lesson=lesson,
            stage_progress=stage_progress,
            stage=request.stage,
            targets=targets,
            current_target=current_target,
            target_progress=target_progress,
            decision=decision,
            conversation_id=conversation_id,
            learner_evidence_allowed=not is_control_message,
            learner_message=request.message,
        )

        reply = decision["reply"]
        if not is_control_message:
            save_conversation_message(
                user.id,
                conversation_id,
                "user",
                request.message,
                db,
            )
        save_conversation_message(
            user.id,
            conversation_id,
            "assistant",
            reply,
            db,
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
            logger.exception("Failed to record structured lesson AI usage.")

        yield sse_event(
            "conversation",
            {"conversation_id": conversation_id},
        )
        yield sse_event(
            "token",
            {"text": reply},
        )
        yield sse_event(
            "decision",
            {
                "action": decision["action"],
                "target_id": current_target["id"],
                "confidence": decision["confidence"],
            },
        )
        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "stage": request.stage,
                "axis_completed": axis_completed,
                "lesson_completed": (
                    request.stage == "practice" and axis_completed
                ),
                "action": (
                    "AXIS_COMPLETE"
                    if axis_completed
                    else decision["action"]
                ),
            },
        )
    except Exception as exc:
        logger.exception("Structured lesson AI stage failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback lesson stage AI transaction."
            )
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
    stage_progress = _get_stage_progress(
        db,
        current_user,
        profile,
        lesson,
    )
    _ensure_stage_open(stage_progress, request.stage)

    if (
        request.stage == "teaching"
        and stage_progress.learn_status != "completed"
    ):
        raise HTTPException(
            status_code=409,
            detail="Teaching requires completed interactive learning.",
        )

    if (
        request.stage == "practice"
        and stage_progress.teaching_status != "completed"
    ):
        raise HTTPException(
            status_code=409,
            detail="Practice requires completed AI teaching.",
        )

    conversation_id = (
        request.conversation_id
        or f"lesson_{request.stage}_{uuid4()}"
    )

    check_rate_limit(user_id=current_user.id)
    usage = get_current_usage(
        user_id=current_user.id,
        db=db,
    )
    if usage.request_count >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Daily AI limit reached.",
        )

    reserve_ai_request(
        user_id=current_user.id,
        db=db,
    )

    now = datetime.utcnow()
    if (
        request.stage == "teaching"
        and stage_progress.teaching_started_at is None
    ):
        stage_progress.teaching_started_at = now
        stage_progress.teaching_status = "available"

    if (
        request.stage == "practice"
        and stage_progress.practice_started_at is None
    ):
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
