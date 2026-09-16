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
from services.ai.conversation import get_conversation_history, save_conversation_message
from services.ai.explanation_language_context import set_explanation_language_context
from services.ai.provider import AI_MODEL, provider
from services.ai.usage import record_api_usage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/lesson", tags=["Lesson AI"])

MAX_HISTORY_MESSAGES = 40
MAX_TEACHING_CONTEXT_MESSAGES = 2
MAX_PRACTICE_CONTEXT_MESSAGES = 4
MAX_HISTORY_CHARS_PER_MESSAGE = 1400
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 420

TARGET_COMPLETE_PATTERN = re.compile(r"\[\[TARGET_COMPLETE:(\d+)\]\]", re.I)
TEACHING_COMPLETE_PATTERN = re.compile(r"\[\[TEACHING_COMPLETE\]\]", re.I)


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=120)


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


def _get_profile(db: Session, user: User, lesson: CourseLesson) -> LearningProfile:
    profile = db.scalar(select(LearningProfile).where(
        LearningProfile.user_id == user.id,
        LearningProfile.language == lesson.language,
    ))
    if profile is None:
        raise HTTPException(status_code=400, detail="Learning profile not found for this lesson language.")
    return profile


def _get_stage_progress(db: Session, user: User, profile: LearningProfile, lesson: CourseLesson) -> UserLessonStageProgress:
    progress = db.scalar(select(UserLessonStageProgress).where(
        UserLessonStageProgress.user_id == user.id,
        UserLessonStageProgress.learning_profile_id == profile.id,
        UserLessonStageProgress.lesson_id == lesson.id,
    ))
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
    if progress.teaching_status == "completed" and progress.practice_status == "locked":
        progress.practice_status = "available"
    return progress


def _ensure_stage_open(progress: UserLessonStageProgress, stage: str) -> None:
    if getattr(progress, f"{stage}_status") == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage '{stage}' is locked until the previous stage is completed.",
        )


def _new_stage_conversation_id(progress: UserLessonStageProgress, stage: str) -> str:
    conversation_id = f"lesson_{stage}_{uuid4()}"
    setattr(progress, f"{stage}_conversation_id", conversation_id)
    return conversation_id


def _get_canonical_conversation_id(progress: UserLessonStageProgress, stage: str) -> str:
    current = str(getattr(progress, f"{stage}_conversation_id", "") or "").strip()
    prefix = f"lesson_{stage}_"
    return current if current.startswith(prefix) else _new_stage_conversation_id(progress, stage)


def _targets(db: Session, lesson_id: int) -> list[dict]:
    rows = db.scalars(select(LessonTarget).where(LessonTarget.lesson_id == lesson_id).order_by(LessonTarget.target_order)).all()
    result = []
    for row in rows:
        patterns = db.scalars(select(LessonTargetPattern).where(
            LessonTargetPattern.target_id == row.id
        ).order_by(LessonTargetPattern.id)).all()
        result.append({
            "order": row.target_order,
            "goal": row.goal,
            "patterns": [p.pattern for p in patterns[:2]],
            "required": row.required,
            "success_criteria": getattr(row, "success_criteria", "") or "",
        })
    return result


def _practice_context(db: Session, lesson_id: int) -> dict | None:
    row = db.scalar(select(LessonPracticeScenario).where(
        LessonPracticeScenario.lesson_id == lesson_id
    ).order_by(LessonPracticeScenario.scenario_order))
    if row is None:
        return None
    return {
        "title": str(row.title or "").strip()[:120],
        "context": str(row.context or "").strip()[:300],
        "instructions": str(row.instructions or "").strip()[:300],
    }


def _remove_control_markers(text: str) -> str:
    text = TARGET_COMPLETE_PATTERN.sub("", text)
    text = TEACHING_COMPLETE_PATTERN.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _raw_history(db: Session, conversation_id: str) -> list:
    return get_conversation_history(
        user_id=None,
        conversation_id=conversation_id,
        max_messages=MAX_HISTORY_MESSAGES,
        db=db,
    )


def _history_messages(rows: list, stage: str) -> list[dict[str, str]]:
    limit = MAX_TEACHING_CONTEXT_MESSAGES if stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES
    messages = []
    for row in rows[-limit:]:
        role = "assistant" if row.role in {"assistant", "model"} else row.role
        if role not in {"user", "assistant"}:
            continue
        content = _remove_control_markers(str(row.content or "").strip())
        if not content:
            continue
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE].rstrip() + "…"
        messages.append({"role": role, "content": content})
    return messages


def _completed_target_orders(rows: list) -> set[int]:
    completed = set()
    for row in rows:
        if row.role not in {"assistant", "model"}:
            continue
        for match in TARGET_COMPLETE_PATTERN.finditer(str(row.content or "")):
            completed.add(int(match.group(1)))
    return completed


def _current_target_order(targets: list[dict], completed: set[int]) -> int | None:
    for target in targets:
        if target["required"] and int(target["order"]) not in completed:
            return int(target["order"])
    return None


def _target_by_order(targets: list[dict], order: int | None) -> dict | None:
    if order is None:
        return None
    return next((t for t in targets if t["required"] and int(t["order"]) == order), None)


def _all_required_targets_completed(targets: list[dict], completed: set[int]) -> bool:
    required = {int(t["order"]) for t in targets if t["required"]}
    return bool(required) and required.issubset(completed)


def _target_needs_teaching(rows: list, current_order: int) -> bool:
    """Keep the teacher in TEACH phase until the current target has been introduced once."""
    last_previous_completion = -1
    for index, row in enumerate(rows):
        for match in TARGET_COMPLETE_PATTERN.finditer(str(row.content or "")):
            if int(match.group(1)) < current_order:
                last_previous_completion = index
    for row in rows[last_previous_completion + 1:]:
        if row.role in {"assistant", "model"} and str(row.content or "").strip():
            return False
    return True


def _teaching_system_prompt(*, lesson, profile, target, current_order, explanation_language, phase, is_start) -> str:
    patterns = " | ".join(str(p).strip() for p in target.get("patterns", []) if str(p).strip())
    success = str(target.get("success_criteria") or "").strip()
    phase_instruction = (
        "You are starting a NEW target. Teach its meaning/function briefly, give ONE concrete model sentence, then ask ONE parallel production prompt. Do not begin with a generic greeting or teacher self-introduction."
        if is_start or phase == "TEACH"
        else "Evaluate ONLY the learner's latest answer. If it is wrong/incomplete, correct the exact mistake as `wrong → correct`, give one short reason, and ask for another attempt at the SAME target. If it is correct, complete the target and immediately begin teaching the next target."
    )
    return f"""
You are the TEACHING AI for a {lesson.level} lesson. You are the teacher, not a practice partner.

LEARNING LANGUAGE: {lesson.language}
LEARNER LEVEL: {profile.level}
EXPLANATION LANGUAGE: {explanation_language}
CURRENT TARGET: {current_order}
TARGET GOAL: {target.get('goal', '')}
TARGET PATTERNS: {patterns}
SUCCESS CRITERIA: {success}
PHASE: {phase}

LANGUAGE LOCK:
- Explanations, corrections, meanings, instructions, evaluations and feedback MUST use {explanation_language}.
- Target sentences, models, examples and the learner's required production MUST use {lesson.language}.
- Do not use the learning language for teacher prose unless it is also the explanation language.
- Never invent the learner's name, location, biography or answer.
- Never use {{name}}, [Name], [name] or <name> as the learner's information. Use a generic example name such as Anna or Thomas when needed.

TEACHING LOGIC:
- {phase_instruction}
- The exact sequence is: TEACH → MODEL → ASK → WAIT → EVALUATE → CORRECT/RETRY → VERIFY → NEXT TARGET.
- Never ask a new target question before showing the learner how to answer it.
- Ask only ONE production question/task per message.
- Do not move to the next target after an unsuccessful attempt.
- Do not treat "yes", "okay", a single name, or vague acknowledgement as mastery when a full sentence is required.
- Accept natural correct alternatives that satisfy the success criteria.
- Do not repeat old teacher text unless repetition is necessary for teaching.
- Keep replies short, normally 1–3 sentences.
- Do not add unrelated topics or suggestions.

OUTPUT:
Return ONLY valid JSON with exactly:
{{"reply":"learner-facing response","target_completed":false,"target_order":{current_order},"stage_completed":false}}

Set target_completed=true only when the learner's latest answer satisfies the current target. On a new/start target, target_completed MUST be false.
""".strip()


def _practice_system_prompt(*, lesson, targets, scenario, is_start, explanation_language) -> str:
    scenario_text = ""
    if scenario:
        scenario_text = f"\nSCENARIO: {scenario['title']}\n{scenario['context']}\n{scenario['instructions']}\n"
    return f"""
You are the PRACTICE AI for a {lesson.level} lesson in {lesson.language}.
Explanation language: {explanation_language}.
{scenario_text}
Respond naturally to the learner. Never invent their personal information or answers. Ask at most one question at a time. Correct meaningful errors briefly. Keep replies short and level-appropriate. Do not output metadata, placeholders or control markers.
{"Begin naturally with one response invitation." if is_start else "Continue from the learner's actual latest message."}
""".strip()


def _parse_teaching_evaluation(raw: str, current_order: int | None, is_control: bool):
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        reply = _remove_control_markers(raw)
        return reply, False, None, False
    if not isinstance(payload, dict):
        raise RuntimeError("Teaching AI returned an invalid evaluation object.")
    reply = str(payload.get("reply") or "").strip()
    if not reply:
        raise RuntimeError("Teaching AI returned no learner-facing reply.")
    try:
        target_order = int(payload["target_order"]) if payload.get("target_order") is not None else None
    except (TypeError, ValueError):
        target_order = None
    completed = (
        not is_control
        and payload.get("target_completed") is True
        and current_order is not None
        and target_order == current_order
    )
    return reply, completed, target_order if completed else None, bool(payload.get("stage_completed")) if completed else False


def _complete_stage(progress, stage: str, conversation_id: str) -> None:
    now = datetime.now(timezone.utc)
    if stage == "teaching":
        progress.teaching_status = "completed"
        progress.teaching_completed_at = now
        progress.teaching_conversation_id = conversation_id
        if progress.practice_status == "locked":
            progress.practice_status = "available"
    else:
        progress.practice_status = "completed"
        progress.practice_completed_at = now
        progress.practice_conversation_id = conversation_id


def _stream_stage_response(*, request, user_id, profile_id, lesson_id, conversation_id):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise RuntimeError("User not found.")
        lesson = _get_lesson(db, lesson_id)
        profile = db.get(LearningProfile, profile_id)
        if profile is None:
            raise RuntimeError("Learning profile not found.")
        progress = _get_stage_progress(db, user, profile, lesson)
        _ensure_stage_open(progress, request.stage)

        mode = str(user.tutor_explanation_language_mode or "native").strip().lower()
        if mode not in {"native", "learning"}:
            mode = "native"
        set_explanation_language_context(
            mode=mode,
            native_language=user.native_language,
            learning_language=lesson.language,
        )
        explanation_language = user.native_language if mode == "native" else lesson.language

        is_control = request.message.strip() == "START_STAGE"
        if is_control:
            conversation_id = _new_stage_conversation_id(progress, request.stage)
            history = []
        else:
            conversation_id = _get_canonical_conversation_id(progress, request.stage)
            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=MAX_HISTORY_MESSAGES,
                db=db,
            )

        if request.stage == "practice" and progress.teaching_status != "completed":
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        required_targets = [t for t in targets if t["required"]]
        if not required_targets:
            raise RuntimeError("Lesson has no required training targets.")

        current_order = _current_target_order(targets, _completed_target_orders(history)) if request.stage == "teaching" else None
        if request.stage == "teaching" and current_order is None:
            completed = _completed_target_orders(history)
            if _all_required_targets_completed(targets, completed):
                _complete_stage(progress, "teaching", conversation_id)
                db.commit()
                yield sse_event("done", {"conversation_id": conversation_id, "stage": "teaching", "axis_completed": True, "lesson_completed": False, "action": "AXIS_COMPLETE", "target_id": None, "confidence": None})
                return
            current_order = int(required_targets[0]["order"])

        messages = _history_messages(history, MAX_TEACHING_CONTEXT_MESSAGES if request.stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES)
        if not is_control:
            messages.append({"role": "user", "content": request.message[:MAX_LEARNER_MESSAGE_CHARS]})
        elif request.stage == "teaching":
            messages.append({"role": "user", "content": "START_STAGE: teach the current target, show one concrete model, then ask exactly one production prompt. Do not greet or introduce yourself."})
        else:
            messages.append({"role": "user", "content": "START_STAGE: begin the practice naturally."})

        if request.stage == "teaching":
            target = _target_by_order(targets, current_order)
            if target is None:
                raise RuntimeError("Current lesson target not found.")
            phase = "TEACH" if is_control or _target_needs_teaching(history, current_order) else "EVALUATE"
            system_prompt = _teaching_system_prompt(
                lesson=lesson,
                profile=profile,
                target=target,
                current_order=current_order,
                explanation_language=explanation_language,
                phase=phase,
                is_start=is_control,
            )
            mime = "application/json"
        else:
            system_prompt = _practice_system_prompt(
                lesson=lesson,
                targets=targets,
                scenario=_practice_context(db, lesson.id),
                is_start=is_control,
                explanation_language=explanation_language,
            )
            mime = None

        response = provider.generate_text(
            model=AI_MODEL,
            prompt=messages,
            system_instruction=system_prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type=mime,
        )
        raw = str(response.text or "").strip()
        if not raw:
            raise RuntimeError("AI tutor returned an empty response.")

        if request.stage == "teaching":
            reply, valid_completion, completed_order, model_stage_complete = _parse_teaching_evaluation(raw, current_order, is_control)
        else:
            reply, valid_completion, completed_order, model_stage_complete = _remove_control_markers(raw), False, None, False
        if not reply:
            raise RuntimeError("AI tutor returned no visible learner-facing text.")

        exchange_count = sum(1 for item in history if item.role == "user")
        if not is_control:
            exchange_count += 1
            save_conversation_message(user.id, conversation_id, "user", request.message[:MAX_LEARNER_MESSAGE_CHARS], db)

        stored_reply = reply
        if valid_completion:
            stored_reply += f"\n[[TARGET_COMPLETE:{completed_order}]]"
            completed = _completed_target_orders(history)
            completed.add(completed_order)
            if _all_required_targets_completed(targets, completed):
                stored_reply += "\n[[TEACHING_COMPLETE]]"
                model_stage_complete = True
        save_conversation_message(user.id, conversation_id, "assistant", stored_reply, db)

        stage_completed = False
        if request.stage == "teaching" and model_stage_complete:
            completed = _completed_target_orders(history)
            if valid_completion:
                completed.add(completed_order)
            if _all_required_targets_completed(targets, completed):
                _complete_stage(progress, "teaching", conversation_id)
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
            logger.exception("Failed to record lesson AI usage.")

        next_order = None
        if request.stage == "teaching" and not stage_completed:
            completed = _completed_target_orders(history)
            if valid_completion:
                completed.add(completed_order)
            next_order = _current_target_order(targets, completed)

        action = "AXIS_COMPLETE" if stage_completed else "TARGET_COMPLETE" if valid_completion else "CONTINUE"
        yield sse_event("conversation", {"conversation_id": conversation_id})
        yield sse_event("token", {"text": reply})
        yield sse_event("decision", {"action": action, "target_id": completed_order if valid_completion else None, "next_target_id": next_order, "confidence": None})
        yield sse_event("done", {
            "conversation_id": conversation_id,
            "stage": request.stage,
            "axis_completed": stage_completed,
            "lesson_completed": request.stage == "practice" and stage_completed,
            "action": action,
            "target_id": completed_order if valid_completion else None,
            "next_target_id": next_order,
            "exchange_count": exchange_count,
        })
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
def lesson_stage_chat(
    request: StageChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = _get_lesson(db, request.lesson_id)
    profile = _get_profile(db, current_user, lesson)
    progress = _get_stage_progress(db, current_user, profile, lesson)
    _ensure_stage_open(progress, request.stage)
    conversation_id = request.conversation_id or ""
    return StreamingResponse(
        _stream_stage_response(
            request=request,
            user_id=current_user.id,
            profile_id=profile.id,
            lesson_id=lesson.id,
            conversation_id=conversation_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
