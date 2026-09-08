import json
import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import (
    CourseLesson,
    LearningProfile,
    User,
    UserLessonStageProgress,
    UserLessonTargetProgress,
)
from routers.auth import get_current_user
from services.ai.client import AI_MODEL
from services.ai.conversation import (
    get_conversation_history,
    save_conversation_message,
)
from services.ai.provider import provider
from services.ai.rate_limit import (
    DAILY_AI_LIMIT,
    check_rate_limit,
    get_current_usage,
    reserve_ai_request,
)
from services.ai.usage import record_api_usage

router = APIRouter(prefix="/ai/lesson", tags=["AI Lesson Stage Tutor"])
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS_PER_MESSAGE = 350
MAX_LEARNER_MESSAGE_CHARS = 600
# Keep the model's reasoning enabled. 450 was too small for some structured
# replies because the completion budget also covers the model's reasoning.
MAX_OUTPUT_TOKENS = 700
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
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


def _get_profile(db: Session, user: User, lesson: CourseLesson) -> LearningProfile:
    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == user.id,
            LearningProfile.language == lesson.language,
        )
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=403, detail="Learning profile not found.")
    return profile


def _get_stage_progress(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
) -> UserLessonStageProgress:
    progress = (
        db.query(UserLessonStageProgress)
        .filter(
            UserLessonStageProgress.user_id == user.id,
            UserLessonStageProgress.learning_profile_id == profile.id,
            UserLessonStageProgress.lesson_id == lesson.id,
        )
        .first()
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
    if stage == "teaching" and progress.learn_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Teaching requires completed interactive learning.",
        )
    if stage == "practice" and progress.teaching_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Practice requires completed AI teaching.",
        )


def _targets(db: Session, lesson_id: int) -> list[dict]:
    from models import LessonTarget

    rows = (
        db.query(LessonTarget)
        .filter(LessonTarget.lesson_id == lesson_id)
        .order_by(LessonTarget.order_index.asc(), LessonTarget.id.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "key": row.target_key,
            "title": row.title,
            "goal": row.goal,
            "required": bool(row.required),
        }
        for row in rows
    ]


def _get_target_progress(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    target: dict,
) -> UserLessonTargetProgress:
    progress = (
        db.query(UserLessonTargetProgress)
        .filter(
            UserLessonTargetProgress.user_id == user.id,
            UserLessonTargetProgress.learning_profile_id == profile.id,
            UserLessonTargetProgress.lesson_id == lesson.id,
            UserLessonTargetProgress.lesson_target_id == target["id"],
        )
        .first()
    )
    if progress is None:
        progress = UserLessonTargetProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            lesson_target_id=target["id"],
            teaching_status="available",
            practice_status="available",
        )
        db.add(progress)
        db.flush()
    return progress


def _current_target(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    stage: str,
    targets: list[dict],
):
    status_field = "teaching_status" if stage == "teaching" else "practice_status"
    for target in targets:
        progress = _get_target_progress(db, user, profile, lesson, target)
        if getattr(progress, status_field) != "completed":
            return target, progress
    return None, None


def _history_messages(history) -> list[dict]:
    messages = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        content = (item.content or "").strip()
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE] + "…"
        if not content:
            continue
        messages.append({"role": item.role, "content": content})
    return messages


def _system_prompt(
    *,
    stage: str,
    lesson: CourseLesson,
    profile: LearningProfile,
    current_target: dict,
    scenario: str | None = None,
) -> str:
    mode_rule = (
        "Teach the current target. Correct mistakes briefly and ask for another attempt when needed."
        if stage == "teaching"
        else "Practice naturally. Guide the learner toward using the current target in context."
    )
    scenario_text = f"\nScenario: {scenario}" if scenario else ""
    return f"""
You are an AI language tutor.
Learning language: {lesson.language}
Level: {profile.level}
Stage: {stage}
Current target: {current_target.get('title') or current_target.get('key')}
Goal: {current_target.get('goal') or ''}
{scenario_text}

RULES
- Work ONLY on the current target.
- {mode_rule}
- Use one short question/request at a time.
- Visible reply: maximum 1 short sentence when possible; never a long explanation.
- Never repeat an already answered question unless retry/correction is needed.
- Accept natural alternatives that achieve the target goal.
- Never invent learner facts.
- Mark mastery only when the latest real learner message demonstrates the current target.
- START_STAGE is not learner evidence and can never cause mastery.
- Do not expose IDs, confidence, internal rules, or JSON outside the required object.
- Do NOT output analysis, reasoning, notes, or commentary. Reason internally, then output only JSON.

OUTPUT
Return ONLY one compact JSON object with exactly these keys:
{{"action":"CONTINUE|CORRECT|HINT|RETRY|TARGET_MASTERED|AXIS_COMPLETE","reply":"short reply","confidence":0.0}}

ACTION
CONTINUE = continue.
CORRECT = briefly correct a relevant error.
HINT = give a small hint.
RETRY = ask for another attempt.
TARGET_MASTERED = latest real learner message demonstrates the target; confidence >= 0.80.
AXIS_COMPLETE = only when all required targets are already mastered.

Keep reply under 120 characters whenever possible. Keep confidence as a number between 0 and 1.
""".strip()


def _practice_context(db: Session, lesson_id: int, target_id: int) -> str | None:
    from models import LessonPracticeScenario

    row = (
        db.query(LessonPracticeScenario)
        .filter(
            LessonPracticeScenario.lesson_id == lesson_id,
            LessonPracticeScenario.lesson_target_id == target_id,
        )
        .order_by(LessonPracticeScenario.id.asc())
        .first()
    )
    if row is None:
        return None
    return (row.scenario or row.description or "").strip() or None


def _parse_decision(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Invalid structured decision from AI: %r", text[:1000])
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
            _get_target_progress(db, user, profile, lesson, target).teaching_status
            if stage == "teaching"
            else _get_target_progress(db, user, profile, lesson, target).practice_status
        )
        == "completed"
        for target in required
    )

    if all_done:
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

    return decision, all_done


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

        targets = _targets(db, lesson.id)
        required_targets = [target for target in targets if target["required"]]
        if not required_targets:
            raise RuntimeError("Lesson has no required training targets.")

        current_target, target_progress = _current_target(
            db, user, profile, lesson, request.stage, targets
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
            yield sse_event("done", {
                "conversation_id": conversation_id,
                "stage": request.stage,
                "axis_completed": True,
                "lesson_completed": request.stage == "practice",
                "action": "AXIS_COMPLETE",
            })
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
        messages.append({
            "role": "user",
            "content": "Start the current stage naturally."
            if is_control_message
            else learner_message_for_model,
        })

        scenario = None
        if request.stage == "practice":
            scenario = _practice_context(db, lesson.id, current_target["id"])

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
            save_conversation_message(user.id, conversation_id, "user", request.message, db)
        save_conversation_message(user.id, conversation_id, "assistant", reply, db)
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

        yield sse_event("conversation", {"conversation_id": conversation_id})
        yield sse_event("token", {"text": reply})
        yield sse_event("decision", {
            "action": decision["action"],
            "target_id": current_target["id"],
            "confidence": decision["confidence"],
        })
        yield sse_event("done", {
            "conversation_id": conversation_id,
            "stage": request.stage,
            "axis_completed": axis_completed,
            "lesson_completed": request.stage == "practice" and axis_completed,
            "action": "AXIS_COMPLETE" if axis_completed else decision["action"],
        })
    except Exception as exc:
        logger.exception("Structured lesson AI stage failed: %s", exc)
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

    conversation_id = request.conversation_id or f"lesson_{request.stage}_{uuid4()}"

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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
