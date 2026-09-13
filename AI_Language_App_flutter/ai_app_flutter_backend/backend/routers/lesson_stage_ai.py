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
MAX_TEACHING_CONTEXT_MESSAGES = 4
MAX_PRACTICE_CONTEXT_MESSAGES = 4
MAX_HISTORY_CHARS_PER_MESSAGE = 1400
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 420

TARGET_COMPLETE_PATTERN = re.compile(r"\[\[TARGET_COMPLETE:(\d+)\]\]", re.IGNORECASE)
TEACHING_COMPLETE_PATTERN = re.compile(r"\[\[TEACHING_COMPLETE\]\]", re.IGNORECASE)


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
    current = getattr(progress, f"{stage}_status")
    if current == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stage '{stage}' is locked until the previous stage is completed.",
        )


def _new_stage_conversation_id(progress: UserLessonStageProgress, stage: str) -> str:
    conversation_id = f"lesson_{stage}_{uuid4()}"
    setattr(progress, f"{stage}_conversation_id", conversation_id)
    return conversation_id


def _get_canonical_conversation_id(progress: UserLessonStageProgress, stage: str) -> str:
    field_name = f"{stage}_conversation_id"
    prefix = f"lesson_{stage}_"
    current = str(getattr(progress, field_name, "") or "").strip()
    if current and current.startswith(prefix):
        return current
    return _new_stage_conversation_id(progress, stage)


def _targets(db: Session, lesson_id: int) -> list[dict]:
    rows = db.scalars(select(LessonTarget).where(LessonTarget.lesson_id == lesson_id).order_by(LessonTarget.target_order)).all()
    result: list[dict] = []
    for row in rows:
        patterns = db.scalars(select(LessonTargetPattern).where(
            LessonTargetPattern.target_id == row.id
        ).order_by(LessonTargetPattern.id)).all()
        result.append({
            "order": row.target_order,
            "goal": row.goal,
            "patterns": [pattern.pattern for pattern in patterns[:2]],
            "required": row.required,
            "success_criteria": getattr(row, "success_criteria", ""),
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
    cleaned = TARGET_COMPLETE_PATTERN.sub("", text)
    cleaned = TEACHING_COMPLETE_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _history_messages(history, max_messages: int) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in history[-max_messages:]:
        role = "assistant" if item.role == "model" else item.role
        if role not in {"user", "assistant"}:
            continue
        content = _remove_control_markers(str(item.content or "").strip())
        if not content:
            continue
        if len(content) > MAX_HISTORY_CHARS_PER_MESSAGE:
            content = content[:MAX_HISTORY_CHARS_PER_MESSAGE].rstrip() + "…"
        result.append({"role": role, "content": content})
    return result


def _completed_target_orders(history) -> list[int]:
    completed: set[int] = set()
    for item in history:
        if item.role not in {"assistant", "model"}:
            continue
        for match in TARGET_COMPLETE_PATTERN.finditer(str(item.content or "")):
            try:
                order = int(match.group(1))
            except ValueError:
                continue
            if order > 0:
                completed.add(order)
    return sorted(completed)


def _current_target_order(targets: list[dict], history) -> int | None:
    required_orders = [int(t["order"]) for t in targets if t["required"] and t.get("order") is not None]
    if not required_orders:
        return None
    completed = set(_completed_target_orders(history))
    for order in required_orders:
        if order not in completed:
            return order
    return None


def _all_required_targets_completed(targets: list[dict], completed_orders: set[int]) -> bool:
    required_orders = {int(t["order"]) for t in targets if t["required"] and t.get("order") is not None}
    return bool(required_orders) and required_orders.issubset(completed_orders)


def _target_by_order(targets: list[dict], target_order: int | None) -> dict | None:
    if target_order is None:
        return None
    for target in targets:
        if target["required"] and target.get("order") is not None and int(target["order"]) == target_order:
            return target
    return None


def _compact_target_goals(targets: list[dict]) -> str:
    lines = []
    for target in targets:
        if not target["required"]:
            continue
        goal = str(target["goal"] or "").strip()
        if goal:
            lines.append(f"{target.get('order')}. {goal}")
    return "\n".join(lines) or "- Follow the lesson objectives."


def _prompt_context(*, lesson: CourseLesson, targets: list[dict], scenario: dict | None = None, include_target_summary: bool = False) -> str:
    context = f"**LANGUAGE**: {lesson.language}\n**LEVEL**: {lesson.level}"
    if include_target_summary:
        context += f"\n\n**LESSON TARGETS**:\n{_compact_target_goals(targets)}"
    if scenario:
        context += (
            f"\n\n**PRACTICE SCENARIO**: {scenario.get('title', '')}\n"
            f"{scenario.get('context', '')}\n{scenario.get('instructions', '')}"
        )
    return context


def _teaching_system_prompt(*, lesson: CourseLesson, targets: list[dict], current_target_order: int | None, is_start: bool) -> str:
    current_target = _target_by_order(targets, current_target_order)
    if current_target is None:
        current_target_text = "**CURRENT TARGET**: There is no remaining target."
    else:
        goal = str(current_target.get("goal", "")).strip()
        patterns = [str(x).strip() for x in current_target.get("patterns", []) if str(x).strip()]
        criteria = str(current_target.get("success_criteria", "")).strip()
        current_target_text = f"**CURRENT TARGET**: {goal}"
        if patterns:
            current_target_text += f"\n**TARGET PATTERNS**: {' | '.join(patterns)}"
        if criteria:
            current_target_text += f"\n**SUCCESS CRITERIA**: {criteria}"

    next_target = None
    if current_target_order is not None:
        for target in targets:
            if target["required"] and target.get("order") is not None and int(target["order"]) > int(current_target_order):
                next_target = target
                break
    if next_target is None:
        next_target_text = "**NEXT TARGET**: None; this is the final required target."
    else:
        next_target_text = f"**NEXT TARGET**: {next_target.get('order')} — {str(next_target.get('goal', '')).strip()}"
        patterns = [str(x).strip() for x in next_target.get("patterns", []) if str(x).strip()]
        if patterns:
            next_target_text += f"\n**NEXT TARGET PATTERNS**: {' | '.join(patterns)}"

    if is_start:
        task = "**START**: This is the first turn. Teach the current target, give a clear model, then ask the learner for one parallel answer."
    else:
        task = "**RESPONSE**: Evaluate the learner's latest answer. If it is not mastered, correct and retry the same target. If it is mastered, teach and model the next target before asking the learner to use it."

    return f"""
You are the **TEACHING AI** for a {lesson.level} language lesson.
You are a professional, patient, academically structured language teacher. You are NOT a casual chatbot and NOT the practice conversation partner.

{_prompt_context(lesson=lesson, targets=targets)}

{current_target_text}
{next_target_text}

**CORE PEDAGOGICAL SEQUENCE — MANDATORY**:
1. TEACH: Explain what the target means and what the learner needs to produce, at the learner's level.
2. MODEL: Give a short, correct example that demonstrates exactly how to answer.
3. ASK: Only after teaching and modeling, ask the learner for one parallel answer.
4. EVALUATE: Judge the learner's latest answer against the target's success criteria.
5. CORRECT: If there is a meaningful error, point to the exact error and show `wrong → correct`, followed by one short explanation.
6. RETRY: Ask the learner to produce the corrected form again. Do not move on yet.
7. VERIFY: Only mark the target complete when the success criteria are actually satisfied.
8. NEXT TARGET: After completion, teach the next target and give its model BEFORE asking the learner to answer it.

**BEFORE EVERY NEW TARGET QUESTION**:
- The learner must first have been taught how to answer the target.
- The reply must contain a short explanation/meaning AND a concrete model/example before the question or prompt.
- Never open a new target with only a question such as "What is your name?" when the required language form has not just been taught.
- For a beginner target, explicitly teach key meanings when useful. Example: `ich = أنا`, `du = أنت`; then model `Ich heiße Anna.`; then ask the learner to make a parallel answer.
- If the target is a question pattern, teach what the question means, show the expected answer pattern, then ask the learner to answer.
- When moving from target N to target N+1, the SAME response may contain success feedback + teaching + model + one prompt for N+1. Do not wait for another turn to teach N+1.

**TARGET PROGRESS RULES**:
- Evaluate ONLY the learner's latest answer for the CURRENT TARGET.
- `target_completed` is true ONLY when the latest learner answer clearly satisfies the SUCCESS CRITERIA.
- If the criteria are not satisfied, stay on the current target.
- Never complete a target merely because the answer is understandable, close, or contains the right general idea.
- Accept natural correct alternatives when they genuinely satisfy the criteria; do not require an identical sentence to the model.
- Once a target is complete, never ask the learner to repeat that same target as a requirement and never pretend it is still incomplete.
- If a next target exists, do not stop after praise. Teach the next target, model it, and give exactly ONE concrete learner prompt in the same reply.
- If the final target is mastered, give brief success feedback and finish the teaching stage.

**ERROR-CORRECTION RULES — MANDATORY**:
- When the learner makes a meaningful language error, identify the exact part that is wrong.
- Show the correction explicitly in the form `wrong → correct`.
- Give one short reason appropriate to the level.
- Then ask the learner to try the corrected target again.
- Example pattern: `Ich heißen → Ich heiße. Bei ich wird heißen zu heiße. Jetzt du: Ich heiße …`
- Do not merely say "incorrect" or provide a corrected sentence without showing where the learner's error was.
- Do not move to a new target until the current target is successfully demonstrated.
- Ignore harmless capitalization, punctuation, spacing, or tiny slips when meaning and the target are clearly correct.
- Do not turn every small mistake into a grammar lecture.

**TEACHING QUALITY RULES**:
- Teach meaning, function, and usable form; do not only test memory.
- The learner should understand what they are supposed to say before being evaluated on it.
- Use short, clear, level-appropriate explanations.
- Prefer one model sentence and one learner prompt over long explanations.
- Ask only ONE learner question or production prompt per message.
- Never answer the learner's production task for them.
- Do not skip the model just because the learner may already know the target; a brief model is still required when introducing a new target.
- If the learner asks for clarification, answer it briefly in the selected explanation language, then return to the current target with teaching/modeling as needed.

**LANGUAGE RULES**:
- The learner is learning the lesson LANGUAGE shown above.
- The selected explanation language supplied by the backend is authoritative.
- ALL teacher explanations, corrections, meanings, grammar notes, instructions, feedback, praise, and ordinary teacher prose MUST use the selected explanation language.
- The learning language may appear in the reply for target words, examples, model sentences, answer patterns, and learner practice content.
- If the explanation language is Arabic and the learning language is German, explain in Arabic and keep German target forms/examples in German.
- A learner may write in the explanation language, learning language, or a mixture. Understand the meaning and do not treat explanation-language usage itself as an error.

**STYLE**:
- Professional teacher tone.
- Warm but concise.
- Normally 1–4 short sentences; use slightly more only when an error needs an explicit correction.
- No unnecessary dialogue, stories, third-party characters, farewells, or topic changes.
- Keep the learner focused on the current target.

{task}

**OUTPUT FORMAT — MANDATORY JSON**:
Return ONLY one valid JSON object with exactly these fields:
{{
  "reply": "the learner-facing teacher message",
  "target_completed": false,
  "target_order": {current_target_order},
  "stage_completed": false
}}

- `reply` contains ONLY learner-facing text. Never put metadata, evaluation notes, JSON, or control markers inside it.
- `target_completed` is true only for the CURRENT TARGET and only when the latest learner answer satisfies its criteria.
- `target_order` is the current target order while evaluating it, or null when there is no current target.
- `stage_completed` is true only when the current target is completed AND it is the final required target.
- When a target is completed and another target exists, `stage_completed` MUST be false.
- The backend remains authoritative for actual lesson state.
""".strip()


def _practice_system_prompt(*, lesson: CourseLesson, targets: list[dict], scenario: dict | None, is_start: bool) -> str:
    task = (
        "**START**: Begin naturally from the scenario, use one suitable target, and invite one response."
        if is_start else
        "**CONTINUE**: Respond to the learner's actual message and use it to continue naturally."
    )
    return f"""
You are the **PRACTICE AI** for a {lesson.level} language lesson.
You are a natural conversation partner, not the formal teacher.

{_prompt_context(lesson=lesson, targets=targets, scenario=scenario, include_target_summary=True)}

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


def _system_prompt(*, stage: str, lesson: CourseLesson, targets: list[dict], scenario: dict | None, current_target_order: int | None, is_start: bool) -> str:
    if stage == "teaching":
        return _teaching_system_prompt(
            lesson=lesson,
            targets=targets,
            current_target_order=current_target_order,
            is_start=is_start,
        )
    return _practice_system_prompt(lesson=lesson, targets=targets, scenario=scenario, is_start=is_start)


def _extract_target_completion(reply: str) -> tuple[str, int | None, bool]:
    target_match = TARGET_COMPLETE_PATTERN.search(reply)
    teaching_complete = bool(TEACHING_COMPLETE_PATTERN.search(reply))
    target_order = None
    if target_match:
        try:
            target_order = int(target_match.group(1))
        except ValueError:
            target_order = None
    return _remove_control_markers(reply), target_order, teaching_complete


def _parse_teaching_evaluation(raw_reply: str, *, current_target_order: int | None, is_control_message: bool) -> tuple[str, bool, int | None, bool]:
    try:
        payload = json.loads(raw_reply)
    except (TypeError, ValueError, json.JSONDecodeError):
        reply, marker_target, teaching_complete = _extract_target_completion(raw_reply)
        valid_marker = (
            not is_control_message
            and marker_target is not None
            and current_target_order is not None
            and marker_target == current_target_order
        )
        return reply, valid_marker, marker_target if valid_marker else None, teaching_complete if valid_marker else False
    if not isinstance(payload, dict):
        raise RuntimeError("Teaching AI returned an invalid evaluation object.")
    reply = str(payload.get("reply") or "").strip()
    if not reply:
        raise RuntimeError("Teaching AI evaluation did not contain a learner-facing reply.")
    target_completed = payload.get("target_completed") is True
    target_order_raw = payload.get("target_order")
    target_order = None
    if target_order_raw is not None:
        try:
            target_order = int(target_order_raw)
        except (TypeError, ValueError):
            target_order = None
    stage_completed = payload.get("stage_completed") is True
    valid_target_completion = (
        not is_control_message
        and target_completed
        and current_target_order is not None
        and target_order == current_target_order
    )
    return reply, valid_target_completion, target_order if valid_target_completion else None, stage_completed if valid_target_completion else False


def _complete_stage(*, stage_progress: UserLessonStageProgress, stage: str, conversation_id: str) -> None:
    now = datetime.now(timezone.utc)
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


def _stream_stage_response(*, request: StageChatRequest, user_id: int, profile_id: int, lesson_id: int, conversation_id: str):
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise RuntimeError("User not found.")

        explanation_mode = str(user.tutor_explanation_language_mode or "native").strip().lower()
        if explanation_mode not in {"native", "learning"}:
            explanation_mode = "native"
        set_explanation_language_context(
            mode=explanation_mode,
            native_language=user.native_language,
            learning_language=user.learning_language,
        )

        lesson = _get_lesson(db, lesson_id)
        profile = db.get(LearningProfile, profile_id)
        if profile is None:
            raise RuntimeError("Learning profile not found.")
        stage_progress = _get_stage_progress(db, user, profile, lesson)
        _ensure_stage_open(stage_progress, request.stage)

        is_control_message = request.message == "START_STAGE"
        if is_control_message:
            conversation_id = _new_stage_conversation_id(stage_progress, request.stage)
            history = []
        else:
            canonical_conversation_id = _get_canonical_conversation_id(stage_progress, request.stage)
            if canonical_conversation_id != conversation_id:
                conversation_id = canonical_conversation_id
            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=MAX_HISTORY_MESSAGES,
                db=db,
            )

        if request.stage == "practice" and stage_progress.teaching_status != "completed":
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        required_targets = [target for target in targets if target["required"]]
        if not required_targets:
            raise RuntimeError("Lesson has no required training targets.")

        current_target_order = None
        if request.stage == "teaching":
            current_target_order = _current_target_order(targets, history)
            if current_target_order is None:
                completed_orders = set(_completed_target_orders(history))
                if _all_required_targets_completed(targets, completed_orders):
                    _complete_stage(stage_progress=stage_progress, stage="teaching", conversation_id=conversation_id)
                    db.commit()
                    yield sse_event("done", {
                        "conversation_id": conversation_id,
                        "stage": "teaching",
                        "axis_completed": True,
                        "lesson_completed": False,
                        "action": "AXIS_COMPLETE",
                        "target_id": None,
                        "confidence": None,
                    })
                    return
                current_target_order = int(required_targets[0]["order"])

        context_limit = MAX_TEACHING_CONTEXT_MESSAGES if request.stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES
        messages = _history_messages(history, context_limit)
        if not is_control_message:
            messages.append({"role": "user", "content": request.message[:MAX_LEARNER_MESSAGE_CHARS]})

        scenario = _practice_context(db, lesson.id) if request.stage == "practice" else None
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
            response_mime_type="application/json" if request.stage == "teaching" else None,
        )
        raw_reply = str(response.text or "").strip()
        if not raw_reply:
            raise RuntimeError("AI tutor returned an empty response.")

        if request.stage == "teaching":
            reply, valid_target_completion, completed_target_order, teaching_complete_marker = _parse_teaching_evaluation(
                raw_reply,
                current_target_order=current_target_order,
                is_control_message=is_control_message,
            )
        else:
            reply, completed_target_order, teaching_complete_marker = _extract_target_completion(raw_reply)
            valid_target_completion = False
        if not reply:
            raise RuntimeError("AI tutor returned no visible learner-facing text.")

        exchange_count_after = sum(1 for item in history if item.role == "user")
        if not is_control_message:
            exchange_count_after += 1
            save_conversation_message(user.id, conversation_id, "user", request.message[:MAX_LEARNER_MESSAGE_CHARS], db)

        stored_assistant_reply = reply
        if valid_target_completion:
            stored_assistant_reply += f"\n[[TARGET_COMPLETE:{completed_target_order}]]"
            completed_orders = set(_completed_target_orders(history))
            completed_orders.add(completed_target_order)
            if _all_required_targets_completed(targets, completed_orders):
                stored_assistant_reply += "\n[[TEACHING_COMPLETE]]"
                teaching_complete_marker = True
        save_conversation_message(user.id, conversation_id, "assistant", stored_assistant_reply, db)

        stage_completed = False
        if request.stage == "teaching":
            completed_orders = set(_completed_target_orders(history))
            if valid_target_completion:
                completed_orders.add(completed_target_order)
            if teaching_complete_marker and _all_required_targets_completed(targets, completed_orders):
                _complete_stage(stage_progress=stage_progress, stage="teaching", conversation_id=conversation_id)
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

        next_target_order = None
        if request.stage == "teaching" and not stage_completed:
            completed_orders = set(_completed_target_orders(history))
            if valid_target_completion:
                completed_orders.add(completed_target_order)
            for target in required_targets:
                order = int(target["order"])
                if order not in completed_orders:
                    next_target_order = order
                    break

        yield sse_event("conversation", {"conversation_id": conversation_id})
        yield sse_event("token", {"text": reply})

        if request.stage == "teaching":
            action = "AXIS_COMPLETE" if stage_completed else "TARGET_COMPLETE" if valid_target_completion else "CONTINUE"
            yield sse_event("decision", {
                "action": action,
                "target_id": completed_target_order if valid_target_completion else None,
                "next_target_id": next_target_order,
                "confidence": None,
            })
        else:
            yield sse_event("decision", {"action": "CONTINUE", "target_id": None, "confidence": None})

        yield sse_event("done", {
            "conversation_id": conversation_id,
            "stage": request.stage,
            "axis_completed": stage_completed,
            "lesson_completed": request.stage == "practice" and stage_completed,
            "action": "AXIS_COMPLETE" if stage_completed else "TARGET_COMPLETE" if valid_target_completion else "CONTINUE",
            "target_id": completed_target_order if valid_target_completion else None,
            "next_target_id": next_target_order,
            "exchange_count": exchange_count_after,
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
