from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
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
MAX_TEACHING_CONTEXT_MESSAGES = 6
MAX_PRACTICE_CONTEXT_MESSAGES = 6
MAX_HISTORY_CHARS_PER_MESSAGE = 1400
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 520

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
    field = f"{stage}_conversation_id"
    prefix = f"lesson_{stage}_"
    current = str(getattr(progress, field, "") or "").strip()
    return current if current.startswith(prefix) else _new_stage_conversation_id(progress, stage)


def _targets(db: Session, lesson_id: int) -> list[dict]:
    rows = db.scalars(select(LessonTarget).where(LessonTarget.lesson_id == lesson_id).order_by(LessonTarget.target_order)).all()
    result = []
    for row in rows:
        patterns = db.scalars(select(LessonTargetPattern).where(
            LessonTargetPattern.target_id == row.id
        ).order_by(LessonTargetPattern.id)).all()
        result.append({
            "order": int(row.target_order),
            "id": str(getattr(row, "target_key", "") or ""),
            "goal": str(row.goal or "").strip(),
            "patterns": [str(p.pattern).strip() for p in patterns[:4] if str(p.pattern or "").strip()],
            "required": bool(row.required),
            "success_criteria": str(getattr(row, "success_criteria", "") or "").strip(),
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


@lru_cache(maxsize=32)
def _load_teaching_specs(language: str, level: str) -> tuple[dict, ...]:
    root = Path(__file__).resolve().parents[1] / "data" / "lessons" / language.lower() / level.upper()
    if not root.exists():
        return ()
    specs = []
    for path in sorted(root.glob("lesson_*/teaching.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            logger.warning("Could not load teaching spec %s", path, exc_info=True)
            continue
        if isinstance(data, dict):
            data["_source_path"] = str(path)
            specs.append(data)
    return tuple(specs)


def _lesson_teaching_spec(lesson: CourseLesson, targets: list[dict]) -> dict:
    specs = _load_teaching_specs(str(lesson.language), str(lesson.level))
    best = {}
    best_score = 0
    for spec in specs:
        items = spec.get("targets")
        if not isinstance(items, list):
            continue
        score = 0
        for target in targets:
            for item in items:
                if not isinstance(item, dict) or int(item.get("order", -1)) != int(target["order"]):
                    continue
                if str(item.get("goal", "")).strip() == target["goal"]:
                    score += 3
                score += 2 * len(set(map(str, item.get("patterns") or [])) & set(target.get("patterns") or []))
        if score > best_score:
            best_score = score
            best = spec
    return best


def _merge_target_spec(target: dict, spec: dict) -> dict:
    merged = dict(target)
    for item in spec.get("targets") or []:
        if not isinstance(item, dict) or int(item.get("order", -1)) != int(target["order"]):
            continue
        if item.get("patterns"):
            merged["patterns"] = [str(x).strip() for x in item["patterns"] if str(x).strip()]
        merged["examples"] = [str(x).strip() for x in item.get("examples") or [] if str(x).strip()]
        if item.get("success_criteria"):
            merged["success_criteria"] = str(item["success_criteria"]).strip()
        break
    return merged


def _remove_control_markers(text: str) -> str:
    text = TARGET_COMPLETE_PATTERN.sub("", text)
    text = TEACHING_COMPLETE_PATTERN.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _history_messages(history, max_messages: int) -> list[dict[str, str]]:
    result = []
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
    completed = set()
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
    completed = set(_completed_target_orders(history))
    for target in targets:
        if target["required"] and int(target["order"]) not in completed:
            return int(target["order"])
    return None


def _all_required_targets_completed(targets: list[dict], completed_orders: set[int]) -> bool:
    required = {int(t["order"]) for t in targets if t["required"]}
    return bool(required) and required.issubset(completed_orders)


def _target_by_order(targets: list[dict], order: int | None) -> dict | None:
    if order is None:
        return None
    return next((t for t in targets if t["required"] and int(t["order"]) == int(order)), None)


def _compact_target_goals(targets: list[dict]) -> str:
    return "\n".join(f"{t['order']}. {t['goal']}" for t in targets if t["required"]) or "- Follow the lesson objectives."


def _target_context(target: dict | None) -> str:
    if not target:
        return "No current target."
    text = [
        f"ORDER: {target['order']}",
        f"ID: {target.get('id', '')}",
        f"GOAL: {target.get('goal', '')}",
        "PATTERNS:\n" + "\n".join(f"- {p}" for p in target.get("patterns", [])),
        f"SUCCESS CRITERIA: {target.get('success_criteria', '')}",
    ]
    examples = target.get("examples") or []
    if examples:
        text.append("APPROVED EXAMPLES:\n" + "\n".join(f"- {e}" for e in examples))
    return "\n".join(text)


def _teaching_system_prompt(*, lesson, targets, current_target_order, is_start, directives) -> str:
    start = (
        "START NOW: do not greet, introduce yourself, or give a generic lesson introduction. "
        "Immediately teach the current target, give one concrete model, then exactly one learner production prompt. "
        "Do not mark the target complete."
        if is_start else
        "CONTINUE: evaluate only the learner's latest answer for the current target. Do not restart the lesson."
    )
    directive_text = "\n".join(f"- {d}" for d in directives) or "- Follow the target sequence and teach before testing."
    return f"""
You are the TEACHING AI for a {lesson.level} lesson in {lesson.language}.
You are a precise teacher, not a generic chatbot.

LESSON TARGETS:
{_compact_target_goals(targets)}

CURRENT TARGET:
{_target_context(_target_by_order(targets, current_target_order))}

LESSON AUTHOR DIRECTIVES:
{directive_text}

MANDATORY STATE MACHINE:
1. TEACH the meaning/function briefly.
2. MODEL one concrete correct sentence.
3. ASK exactly one concrete production prompt.
4. EVALUATE only the latest learner answer.
5. CORRECT meaningful errors using `wrong → correct` plus one short reason.
6. RETRY the same target after an error.
7. VERIFY the target before completion.
8. Only after completion, teach and model the next target before asking for it.

STRICT RULES:
- Never invent the learner's name, location, biography, or answer.
- Never output {{name}}, [Name], [name], or <name> as if it were the learner's information.
- If a model needs a name, use a clearly generic example such as Anna or Thomas.
- Never start with "Hallo! Ich bin dein Deutschlehrer" or another generic self-introduction.
- Never ask a target question before teaching how to answer it.
- Exactly one learner question/production prompt per message.
- No "and something else", unrelated suggestions, stories, or topic changes.
- Do not repeat old teacher text unless repetition is necessary for teaching.
- "yes", "okay", a single name, or vague acknowledgement is not mastery when a full sentence is required.
- Do not move to the next target after an unsuccessful attempt.
- Keep normal replies to 2–4 short sentences.
- The learner-facing reply contains only learner-facing text.

LANGUAGE RULES:
- The lesson language is {lesson.language}.
- The backend-selected explanation language is authoritative.
- Explanations, corrections, meanings, instructions, feedback and ordinary teacher prose use that explanation language.
- Target sentences, examples and required learner production use the lesson language.
- Never silently switch teacher prose to English.

{start}

OUTPUT ONLY JSON:
{{
  "reply": "learner-facing teacher message",
  "target_completed": false,
  "target_order": {json.dumps(current_target_order)},
  "stage_completed": false
}}
""".strip()


def _practice_system_prompt(*, lesson, targets, scenario, is_start) -> str:
    scenario_text = ""
    if scenario:
        scenario_text = f"\nSCENARIO: {scenario.get('title', '')}\n{scenario.get('context', '')}\n{scenario.get('instructions', '')}\n"
    return f"""
You are the PRACTICE AI for a {lesson.level} lesson in {lesson.language}.
You are a natural conversation partner, not a formal teacher.

LESSON TARGETS:
{_compact_target_goals(targets)}
{scenario_text}
RULES:
- Respond to the learner's actual message.
- Never invent the learner's answer or personal information.
- Use targets naturally; do not force a checklist.
- Ask at most one natural question at a time.
- Correct meaningful errors briefly.
- Keep replies short and level-appropriate.
- No generic introductions, placeholders, unrelated topics, metadata, or control markers.

{"Begin naturally from the scenario with one response invitation." if is_start else "Continue naturally from the learner's latest message."}
""".strip()


def _system_prompt(*, stage, lesson, targets, scenario, current_target_order, is_start, directives):
    if stage == "teaching":
        return _teaching_system_prompt(
            lesson=lesson,
            targets=targets,
            current_target_order=current_target_order,
            is_start=is_start,
            directives=directives,
        )
    return _practice_system_prompt(lesson=lesson, targets=targets, scenario=scenario, is_start=is_start)


def _parse_teaching_evaluation(raw_reply: str, current_target_order: int | None, is_control_message: bool):
    try:
        payload = json.loads(raw_reply)
    except (TypeError, ValueError, json.JSONDecodeError):
        reply = _remove_control_markers(raw_reply)
        return reply, False, None, False
    if not isinstance(payload, dict):
        raise RuntimeError("Teaching AI returned an invalid evaluation object.")
    reply = str(payload.get("reply") or "").strip()
    if not reply:
        raise RuntimeError("Teaching AI returned no learner-facing reply.")
    target_order = None
    try:
        if payload.get("target_order") is not None:
            target_order = int(payload.get("target_order"))
    except (TypeError, ValueError):
        pass
    completed = (
        not is_control_message
        and payload.get("target_completed") is True
        and current_target_order is not None
        and target_order == current_target_order
    )
    return reply, completed, target_order if completed else None, bool(payload.get("stage_completed")) if completed else False


def _complete_stage(*, stage_progress, stage, conversation_id):
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


def _validate_start_reply(reply: str, target: dict | None) -> None:
    if target is None:
        raise RuntimeError("No current teaching target is available.")
    if re.search(r"\{\s*name\s*\}|\[\s*name\s*\]|<\s*name\s*>", reply, re.IGNORECASE):
        raise RuntimeError("Teaching AI used a learner-name placeholder in the opening response.")
    patterns = [p for p in target.get("patterns", []) if p]
    if patterns and not any(p.lower().replace("[name]", "").strip() in reply.lower() for p in patterns):
        raise RuntimeError("Teaching AI opening response did not teach the current target pattern.")


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
        stage_progress = _get_stage_progress(db, user, profile, lesson)
        _ensure_stage_open(stage_progress, request.stage)

        explanation_mode = str(user.tutor_explanation_language_mode or "native").strip().lower()
        if explanation_mode not in {"native", "learning"}:
            explanation_mode = "native"
        set_explanation_language_context(
            mode=explanation_mode,
            native_language=user.native_language,
            learning_language=lesson.language,
        )

        is_control_message = request.message.strip() == "START_STAGE"
        if is_control_message:
            conversation_id = _new_stage_conversation_id(stage_progress, request.stage)
            history = []
        else:
            conversation_id = _get_canonical_conversation_id(stage_progress, request.stage)
            history = get_conversation_history(
                user_id=user.id,
                conversation_id=conversation_id,
                max_messages=MAX_HISTORY_MESSAGES,
                db=db,
            )

        if request.stage == "practice" and stage_progress.teaching_status != "completed":
            raise RuntimeError("Practice requires completed AI teaching.")

        targets = _targets(db, lesson.id)
        required_targets = [t for t in targets if t["required"]]
        if not required_targets:
            raise RuntimeError("Lesson has no required training targets.")

        spec = _lesson_teaching_spec(lesson, targets) if request.stage == "teaching" else {}
        if spec:
            targets = [_merge_target_spec(t, spec) for t in targets]
            required_targets = [t for t in targets if t["required"]]
        directives = [str(x).strip() for x in spec.get("behavior_directives") or [] if str(x).strip()]

        current_target_order = _current_target_order(targets, history) if request.stage == "teaching" else None
        if request.stage == "teaching" and current_target_order is None:
            completed = set(_completed_target_orders(history))
            if _all_required_targets_completed(targets, completed):
                _complete_stage(stage_progress=stage_progress, stage="teaching", conversation_id=conversation_id)
                db.commit()
                yield sse_event("done", {"conversation_id": conversation_id, "stage": "teaching", "axis_completed": True, "lesson_completed": False, "action": "AXIS_COMPLETE", "target_id": None, "confidence": None})
                return
            current_target_order = int(required_targets[0]["order"])

        messages = _history_messages(
            history,
            MAX_TEACHING_CONTEXT_MESSAGES if request.stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES,
        )
        if is_control_message:
            messages.append({
                "role": "user",
                "content": (
                    "START_STAGE command. Do not greet or introduce yourself. "
                    "Immediately teach the current target, show one concrete model, and give exactly one learner production prompt."
                    if request.stage == "teaching" else
                    "START_STAGE command. Begin the practice naturally."
                ),
            })
        else:
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
                directives=directives,
            ),
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type="application/json" if request.stage == "teaching" else None,
        )
        raw_reply = str(response.text or "").strip()
        if not raw_reply:
            raise RuntimeError("AI tutor returned an empty response.")

        if request.stage == "teaching":
            reply, valid_completion, completed_target_order, teaching_complete = _parse_teaching_evaluation(raw_reply, current_target_order, is_control_message)
            if is_control_message:
                _validate_start_reply(reply, _target_by_order(targets, current_target_order))
                valid_completion = False
                completed_target_order = None
                teaching_complete = False
        else:
            reply = _remove_control_markers(raw_reply)
            valid_completion = False
            completed_target_order = None
            teaching_complete = False

        history_user_count = sum(1 for item in history if item.role == "user")
        if not is_control_message:
            history_user_count += 1
            save_conversation_message(user.id, conversation_id, "user", request.message[:MAX_LEARNER_MESSAGE_CHARS], db)

        stored_reply = reply
        if valid_completion:
            stored_reply += f"\n[[TARGET_COMPLETE:{completed_target_order}]]"
            completed = set(_completed_target_orders(history))
            completed.add(completed_target_order)
            if _all_required_targets_completed(targets, completed):
                stored_reply += "\n[[TEACHING_COMPLETE]]"
                teaching_complete = True
        save_conversation_message(user.id, conversation_id, "assistant", stored_reply, db)

        stage_completed = False
        if request.stage == "teaching":
            completed = set(_completed_target_orders(history))
            if valid_completion:
                completed.add(completed_target_order)
            if teaching_complete and _all_required_targets_completed(targets, completed):
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

        next_target = None
        if request.stage == "teaching" and not stage_completed:
            completed = set(_completed_target_orders(history))
            if valid_completion:
                completed.add(completed_target_order)
            for target in required_targets:
                if int(target["order"]) not in completed:
                    next_target = int(target["order"])
                    break

        yield sse_event("conversation", {"conversation_id": conversation_id})
        yield sse_event("token", {"text": reply})
        action = "AXIS_COMPLETE" if stage_completed else "TARGET_COMPLETE" if valid_completion else "CONTINUE"
        yield sse_event("decision", {
            "action": action,
            "target_id": completed_target_order if valid_completion else None,
            "next_target_id": next_target,
            "confidence": None,
        })
        yield sse_event("done", {
            "conversation_id": conversation_id,
            "stage": request.stage,
            "axis_completed": stage_completed,
            "lesson_completed": request.stage == "practice" and stage_completed,
            "action": action,
            "target_id": completed_target_order if valid_completion else None,
            "next_target_id": next_target,
            "exchange_count": history_user_count,
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
    return StreamingResponse(
        _stream_stage_response(
            request=request,
            user_id=current_user.id,
            profile_id=profile.id,
            lesson_id=lesson.id,
            conversation_id=request.conversation_id or "",
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
