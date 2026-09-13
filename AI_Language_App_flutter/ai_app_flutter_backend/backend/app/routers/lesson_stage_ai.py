from __future__

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
from services.ai.explanation_language_context import (
    set_explanation_language_context,
)
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

TARGET_COMPLETE_PATTERN = re.compile(r"\[\[TARGET_COMPLETE:(\d+)\]\]", re.IGNORECASE)
TEACHING_COMPLETE_PATTERN = re.compile(r"\[\[TEACHING_COMPLETE\]\]", re.IGNORECASE)


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=120)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.scalar(select(CourseLesson).where(CourseLesson.id == lesson_id))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _get_profile(db: Session, user_id: int, language: str) -> LearningProfile:
    profile = db.scalar(
        select(LearningProfile).where(
            LearningProfile.user_id == user_id,
            LearningProfile.language == language,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Learning profile not found")
    return profile


def _get_stage_progress(
    db: Session,
    user_id: int,
    lesson_id: int,
) -> UserLessonStageProgress:
    progress = db.scalar(
        select(UserLessonStageProgress).where(
            UserLessonStageProgress.user_id == user_id,
            UserLessonStageProgress.lesson_id == lesson_id,
        )
    )
    if progress is None:
        progress = UserLessonStageProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            teaching_available=True,
            practice_available=False,
            teaching_completed=False,
            practice_completed=False,
        )
        db.add(progress)
        db.flush()
    return progress


def _ensure_stage_open(progress: UserLessonStageProgress, stage: str) -> None:
    if stage == "teaching" and not progress.teaching_available:
        raise HTTPException(status_code=409, detail="Teaching stage is not available")
    if stage == "practice" and not progress.practice_available:
        raise HTTPException(status_code=409, detail="Practice stage is not available")


def _new_stage_conversation_id(stage: str, lesson_id: int, user_id: int) -> str:
    return f"lesson_{stage}_{lesson_id}_{user_id}_{uuid4().hex[:10]}"


def _get_canonical_conversation_id(
    requested: str | None,
    stage: str,
    lesson_id: int,
    user_id: int,
) -> str:
    if requested and requested.startswith(f"lesson_{stage}_{lesson_id}_{user_id}_"):
        return requested
    return _new_stage_conversation_id(stage, lesson_id, user_id)


def _targets(db: Session, lesson_id: int) -> list[dict]:
    rows = db.scalars(
        select(LessonTarget)
        .where(LessonTarget.lesson_id == lesson_id)
        .order_by(LessonTarget.target_order)
    ).all()

    result = []
    for target in rows:
        patterns = db.scalars(
            select(LessonTargetPattern)
            .where(LessonTargetPattern.target_id == target.id)
            .order_by(LessonTargetPattern.id)
            .limit(2)
        ).all()
        result.append(
            {
                "order": target.target_order,
                "goal": target.goal,
                "patterns": [p.pattern for p in patterns],
                "success_criteria": target.success_criteria,
            }
        )
    return result


def _practice_context(db: Session, lesson_id: int) -> str:
    scenarios = db.scalars(
        select(LessonPracticeScenario)
        .where(LessonPracticeScenario.lesson_id == lesson_id)
        .order_by(LessonPracticeScenario.id)
        .limit(4)
    ).all()
    if not scenarios:
        return ""
    return "\n".join(
        f"- {s.title}: {s.description}" for s in scenarios if s.title or s.description
    )


def _remove_control_markers(text: str) -> str:
    text = TARGET_COMPLETE_PATTERN.sub("", text)
    text = TEACHING_COMPLETE_PATTERN.sub("", text)
    return text.strip()


def _history_messages(
    db: Session,
    conversation_id: str,
    stage: str,
) -> list[dict]:
    limit = MAX_TEACHING_CONTEXT_MESSAGES if stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES
    rows = get_conversation_history(
        db,
        conversation_id=conversation_id,
        limit=MAX_HISTORY_MESSAGES,
    )
    messages = []
    for row in rows[-limit:]:
        role = "assistant" if row.role == "assistant" else "user"
        content = _remove_control_markers((row.content or "").strip())
        if not content:
            continue
        messages.append(
            {
                "role": role,
                "content": content[:MAX_HISTORY_CHARS_PER_MESSAGE],
            }
        )
    return messages


def _completed_target_orders(history: list[dict]) -> set[int]:
    completed: set[int] = set()
    for message in history:
        for match in TARGET_COMPLETE_PATTERN.finditer(message.get("content", "")):
            completed.add(int(match.group(1)))
    return completed


def _current_target_order(targets: list[dict], completed: set[int]) -> int | None:
    for target in targets:
        order = int(target["order"])
        if order not in completed:
            return order
    return None


def _all_required_targets_completed(targets: list[dict], completed: set[int]) -> bool:
    return bool(targets) and all(int(t["order"]) in completed for t in targets)


def _target_by_order(targets: list[dict], order: int | None) -> dict | None:
    if order is None:
        return None
    return next((t for t in targets if int(t["order"]) == order), None)


def _compact_target_goals(targets: list[dict]) -> str:
    return "\n".join(
        f"{t['order']}. {t['goal']}" for t in targets if t.get("goal")
    )


def _prompt_context(
    lesson: CourseLesson,
    profile: LearningProfile,
    targets: list[dict],
    current_order: int | None,
    explanation_language: str,
    practice_context: str,
) -> str:
    current = _target_by_order(targets, current_order)
    lines = [
        f"Learning language: {lesson.language}",
        f"Learner level: {profile.level}",
        f"Selected explanation language: {explanation_language}",
        f"Current target order: {current_order}",
        f"Current target goal: {current.get('goal', '') if current else ''}",
    ]
    if current and current.get("patterns"):
        lines.append("Current target patterns: " + " | ".join(current["patterns"]))
    if current and current.get("success_criteria"):
        lines.append("Current target success criteria: " + str(current["success_criteria"]))
    if practice_context:
        lines.append("Practice scenarios:\n" + practice_context)
    return "\n".join(lines)


def _teaching_system_prompt(
    lesson: CourseLesson,
    profile: LearningProfile,
    targets: list[dict],
    current_order: int,
    explanation_language: str,
) -> str:
    current = _target_by_order(targets, current_order) or {}
    current_patterns = " | ".join(current.get("patterns", []))

    next_target = next(
        (t for t in targets if int(t["order"]) > current_order),
        None,
    )
    next_patterns = " | ".join(next_target.get("patterns", [])) if next_target else ""

    context = _prompt_context(
        lesson,
        profile,
        targets,
        current_order,
        explanation_language,
        "",
    )

    return f"""You are the TEACHING AI for a language lesson.

{context}

Teach only the CURRENT TARGET. You are the teacher, not a practice partner.

CURRENT TARGET:
Goal: {current.get('goal', '')}
Patterns: {current_patterns}
Success criteria: {current.get('success_criteria', '')}

NEXT TARGET (only after current target is completed):
Goal: {next_target.get('goal', '') if next_target else ''}
Patterns: {next_patterns}

TEACHING METHOD:
- Never ask the learner to produce a new target before teaching it.
- For a new target, use this sequence: Teach → Model → Ask → Wait → Evaluate → Correct/Retry → Complete.
- Before the first question/prompt for the current target, give a short model or answer pattern in the learning language and the minimum explanation needed in the selected explanation language.
- After modeling, ask for one parallel answer. Do not provide the exact answer when the learner is supposed to produce it.
- If the learner makes a meaningful error, point to the exact wrong part, show `wrong → correct`, give one short reason, then ask for another attempt at the SAME target.
- Do not mark the current target complete after an incorrect or incomplete answer.
- Do not move to the next target until the current target's success criteria are satisfied.
- Once the current target is completed, the next response must BEGIN teaching the next target. If the next target needs a model, provide it first, then ask the learner. Never jump directly to an unexplained question.
- Accept natural correct answers; do not require the exact model wording when another answer satisfies the target.
- Do not over-correct mistakes unrelated to the current target.
- Keep corrections and explanations brief and level-appropriate.

LANGUAGE RULES:
- The learner is learning {lesson.language}.
- Use {explanation_language} for explanations, corrections, and feedback.
- Use {lesson.language} for target sentences, models, examples, and learner-facing practice content.
- The learner may answer in either language when needed.

GENERAL RULES:
- Respond to the learner's actual latest message.
- One simple question or task at a time.
- Keep replies short: normally 1–3 short sentences.
- Do not start unrelated dialogue or farewells.
- Wait for the learner's attempt before changing topic.

OUTPUT:
Return ONLY valid JSON. Do not use Markdown fences. Do not add any text before or after the JSON.
Use exactly this shape:
{{"reply":"short learner-facing response","target_completed":false,"target_order":{current_order},"stage_completed":false}}

Set target_completed=true only when the learner's latest answer satisfies the current target's success criteria.
Set stage_completed=true only when all required targets are complete.
"""


def _practice_system_prompt(
    lesson: CourseLesson,
    profile: LearningProfile,
    targets: list[dict],
    explanation_language: str,
    practice_context: str,
) -> str:
    context = _prompt_context(
        lesson,
        profile,
        targets,
        None,
        explanation_language,
        practice_context,
    )
    return f"""You are the PRACTICE AI for a language lesson.

{context}

Have a natural practice conversation using the lesson targets.
- You are a conversation partner, not a formal teacher.
- Let the learner drive the interaction.
- Ask one natural question at a time.
- Keep replies short and level-appropriate.
- Correct meaningful errors briefly, then continue naturally.
- Do not turn practice into a grammar lesson.
- Use the learning language for the conversation; use the selected explanation language only when a brief explanation is needed.
- Do not output JSON, control markers, Markdown, or meta-commentary.
"""


def _system_prompt(
    stage: str,
    lesson: CourseLesson,
    profile: LearningProfile,
    targets: list[dict],
    current_order: int | None,
    explanation_language: str,
    practice_context: str,
) -> str:
    if stage == "teaching":
        assert current_order is not None
        return _teaching_system_prompt(
            lesson,
            profile,
            targets,
            current_order,
            explanation_language,
        )
    return _practice_system_prompt(
        lesson,
        profile,
        targets,
        explanation_language,
        practice_context,
    )


def _parse_teaching_evaluation(text: str, current_order: int) -> tuple[str, bool, bool]:
    raw = text.strip()
    candidate = raw

    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate).strip()

    data = None
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{\s*\"reply\"\s*:\s*.*\}\s*$", candidate, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = None

    if isinstance(data, dict):
        reply = str(data.get("reply", "")).strip()
        target_order = data.get("target_order")
        target_completed = data.get("target_completed") is True
        stage_completed = data.get("stage_completed") is True

        if reply:
            if target_order != current_order:
                target_completed = False
            return _remove_control_markers(reply), target_completed, stage_completed

    fallback = _remove_control_markers(raw)
    return fallback, False, False


def _stream_stage_response(
    *,
    user_id: int,
    request: StageChatRequest,
):
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.id == user_id))
        if user is None:
            yield _sse("error", {"message": "User not found"})
            return

        lesson = _get_lesson(db, request.lesson_id)
        profile = _get_profile(db, user.id, lesson.language)
        progress = _get_stage_progress(db, user.id, lesson.id)
        _ensure_stage_open(progress, request.stage)

        explanation_language = getattr(user, "tutor_explanation_language_mode", None) or user.native_language or "en"
        set_explanation_language_context(explanation_language)

        targets = _targets(db, lesson.id)
        if not targets:
            yield _sse("error", {"message": "Lesson has no targets"})
            return

        control_message = request.message == "START_STAGE"
        conversation_id = (
            _new_stage_conversation_id(request.stage, lesson.id, user.id)
            if control_message
            else _get_canonical_conversation_id(
                request.conversation_id,
                request.stage,
                lesson.id,
                user.id,
            )
        )

        history = [] if control_message else _history_messages(db, conversation_id, request.stage)
        completed = _completed_target_orders(history)

        if request.stage == "teaching":
            current_order = _current_target_order(targets, completed)
            if current_order is None:
                if not progress.teaching_completed:
                    progress.teaching_completed = True
                    progress.practice_available = True
                    db.commit()
                yield _sse("conversation", {"conversation_id": conversation_id})
                yield _sse("done", {"conversation_id": conversation_id, "axis_completed": True})
                return
        else:
            current_order = None

        system_prompt = _system_prompt(
            request.stage,
            lesson,
            profile,
            targets,
            current_order,
            explanation_language,
            _practice_context(db, lesson.id),
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        if not control_message:
            messages.append({"role": "user", "content": request.message[:MAX_LEARNER_MESSAGE_CHARS]})
        else:
            messages.append(
                {
                    "role": "user",
                    "content": "Begin the current lesson target. Teach it before asking the learner to produce it.",
                }
            )

        result = provider.generate_text(
            model=AI_MODEL,
            messages=messages,
            max_tokens=MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"} if request.stage == "teaching" else None,
        )

        raw_text = (result.text or "").strip()
        if not raw_text:
            yield _sse("error", {"message": "AI returned no final text"})
            return

        target_completed = False
        stage_completed = False
        if request.stage == "teaching":
            reply, target_completed, stage_completed = _parse_teaching_evaluation(
                raw_text,
                current_order,
            )
        else:
            reply = _remove_control_markers(raw_text)

        if not reply:
            yield _sse("error", {"message": "AI returned an empty learner-facing reply"})
            return

        if not control_message:
            save_conversation_message(
                db,
                conversation_id=conversation_id,
                role="user",
                content=request.message[:MAX_LEARNER_MESSAGE_CHARS],
            )

        assistant_content = reply
        if request.stage == "teaching" and target_completed:
            assistant_content += f" [[TARGET_COMPLETE:{current_order}]]"

            completed.add(current_order)
            if _all_required_targets_completed(targets, completed):
                stage_completed = True
                assistant_content += " [[TEACHING_COMPLETE]]"
                progress.teaching_completed = True
                progress.practice_available = True

        save_conversation_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        db.commit()

        try:
            record_api_usage(
                db,
                user_id=user.id,
                model=AI_MODEL,
                input_tokens=getattr(result, "input_tokens", 0) or 0,
                output_tokens=getattr(result, "output_tokens", 0) or 0,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to record lesson AI usage")

        yield _sse("conversation", {"conversation_id": conversation_id})
        yield _sse(
            "token",
            {
                "text": reply,
                "conversation_id": conversation_id,
            },
        )
        yield _sse(
            "decision",
            {
                "target_completed": target_completed,
                "target_order": current_order,
                "stage_completed": stage_completed,
            },
        )
        yield _sse(
            "done",
            {
                "conversation_id": conversation_id,
                "axis_completed": stage_completed,
            },
        )
    except HTTPException as exc:
        db.rollback()
        yield _sse("error", {"message": exc.detail})
    except Exception:
        db.rollback()
        logger.exception("Lesson stage AI failed")
        yield _sse("error", {"message": "Lesson AI request failed"})
    finally:
        db.close()


@router.post("/stage-chat")
def stage_chat(
    request: StageChatRequest,
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        _stream_stage_response(user_id=current_user.id, request=request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
