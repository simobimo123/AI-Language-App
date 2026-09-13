from __future__ import annotations

import json
import logging
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
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


def _raw_history(db: Session, conversation_id: str) -> list:
    return get_conversation_history(
        db,
        conversation_id=conversation_id,
        limit=MAX_HISTORY_MESSAGES,
    )


def _completed_target_orders(rows: list) -> set[int]:
    completed: set[int] = set()
    for row in rows:
        for match in TARGET_COMPLETE_PATTERN.finditer(row.content or ""):
            completed.add(int(match.group(1)))
    return completed


def _history_messages(rows: list, stage: str) -> list[dict]:
    limit = MAX_TEACHING_CONTEXT_MESSAGES if stage == "teaching" else MAX_PRACTICE_CONTEXT_MESSAGES
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


def _target_needs_teaching(rows: list, current_order: int) -> bool:
    """True when the current target has not received a teaching/model response yet."""
    last_completed_index = -1
    for index, row in enumerate(rows):
        content = row.content or ""
        matches = list(TARGET_COMPLETE_PATTERN.finditer(content))
        if any(int(m.group(1)) < current_order for m in matches):
            last_completed_index = index

    for row in rows[last_completed_index + 1 :]:
        if row.role == "assistant" and (row.content or "").strip():
            return False
    return True


def _prompt_context(
    lesson: CourseLesson,
    profile: LearningProfile,
    target: dict,
    current_order: int,
    explanation_language: str,
    phase: str,
) -> str:
    lines = [
        f"Learning language: {lesson.language}",
        f"Learner level: {profile.level}",
        f"Explanation language: {explanation_language}",
        f"Current target: {current_order}",
        f"Target goal: {target.get('goal', '')}",
        f"Target patterns: {' | '.join(target.get('patterns', []))}",
        f"Success criteria: {target.get('success_criteria', '')}",
        f"Phase: {phase}",
    ]
    return "\n".join(lines)


def _teaching_system_prompt(
    lesson: CourseLesson,
    profile: LearningProfile,
    target: dict,
    current_order: int,
    explanation_language: str,
    phase: str,
) -> str:
    context = _prompt_context(
        lesson,
        profile,
        target,
        current_order,
        explanation_language,
        phase,
    )

    return f"""You are the TEACHING AI. Follow the rules below exactly.

{context}

LANGUAGE LOCK:
- The learning language is {lesson.language}.
- The explanation language is {explanation_language}.
- ALL explanations, corrections, evaluations, grammar comments, instructions, and feedback MUST be in {explanation_language}.
- NEVER explain or correct in {lesson.language} unless {lesson.language} is also the explanation language.
- {lesson.language} may appear only inside a target sentence, model, example, question, or learner-production prompt.
- Keep target-language examples short and clearly separated from the explanation.

TEACHING LOCK:
- Current phase is {phase}.
- If phase = TEACH, you MUST teach/model BEFORE asking the learner anything.
- In TEACH phase, do NOT start with a question. First give a short explanation in {explanation_language}, then one simple model in {lesson.language}, then ask the learner to produce a parallel answer.
- After the learner answers, evaluate ONLY the current target.
- If the answer is wrong or incomplete, DO NOT move forward.
- Identify the exact incorrect part from the learner's answer.
- Correction format: `wrong part → correct part` followed by ONE short explanation in {explanation_language}, then ask the learner to retry the SAME target.
- Never say only "wrong", "incorrect", "try again", or a vague correction.
- Do not mark a target complete unless the latest learner answer satisfies its success criteria.
- When a target is completed, the next target starts in TEACH phase: explain/model it before asking.
- One learner task at a time. Keep replies short.

ERROR TOLERANCE:
- Distinguish between meaningful language errors and harmless surface/formality issues.
- IGNORE minor capitalization differences, especially capitalization at the beginning of a sentence or proper-name capitalization, when the intended meaning is clear and the learner's language is otherwise correct.
- IGNORE minor punctuation, spacing, apostrophe/typographic, or formatting differences when they do not change meaning or grammatical correctness.
- IGNORE harmless spelling/typing slips when the intended word is obvious and the slip does not create ambiguity or change the meaning.
- Do NOT interrupt the learner's progress for these harmless issues.
- Do NOT require the learner to reproduce capitalization or punctuation perfectly unless the lesson explicitly teaches that feature.
- HOWEVER, DO correct genuine grammar, word-order, agreement, conjugation, article, preposition, pronoun, or meaning-changing errors, even when the rest of the sentence is understandable.
- If an error changes or obscures the meaning, treat it as meaningful and correct it.
- If a sentence is grammatically acceptable and natural for the learner's CEFR level, accept it even if it differs from the model or uses a valid alternative.
- Do not invent an error merely because the learner used a different correct expression.
- Apply this tolerance consistently in both target evaluation and correction decisions.
- Example of harmless issue: `ich heiße Thomas` when the expected form is `Ich heiße Thomas` → accept; do not stop the lesson for capitalization.
- Example of meaningful issue: `Ich bist Thomas` → correct `bist → bin`, because this is a real conjugation error.

CORRECTION QUALITY:
- For a meaningful error, show exactly where it occurred using `wrong part → correct part`.
- Explain the reason briefly in {explanation_language}.
- If several meaningful errors exist, prioritize the error most relevant to the current target and avoid overwhelming the learner.
- Never turn a harmless typo/capitalization issue into a grammar correction.
- Never claim that a capitalization-only difference makes an otherwise correct answer wrong.

OUTPUT LANGUAGE EXAMPLES:
- Explanation: {explanation_language}.
- Model/question: {lesson.language}.
- Correction explanation: {explanation_language}.
Do not mix these roles.

OUTPUT:
Return ONLY valid JSON, with no Markdown fences:
{{"reply":"learner-facing response","target_completed":false,"target_order":{current_order},"stage_completed":false}}

Set target_completed=true only if the latest learner answer is correct for this target after applying the ERROR TOLERANCE rules.
Set stage_completed=true only if all targets are complete.
"""


def _practice_system_prompt(
    lesson: CourseLesson,
    profile: LearningProfile,
    targets: list[dict],
    explanation_language: str,
    practice_context: str,
) -> str:
    target_lines = " | ".join(
        f"{t['order']}: {t.get('goal', '')}" for t in targets
    )
    context = (
        f"Learning language: {lesson.language}\n"
        f"Learner level: {profile.level}\n"
        f"Explanation language: {explanation_language}\n"
        f"Targets: {target_lines}"
    )
    if practice_context:
        context += "\nScenarios:\n" + practice_context

    return f"""You are the PRACTICE AI.

{context}

- Conversation uses {lesson.language}.
- Explanations and corrections use {explanation_language}.
- Keep replies short and natural.
- Correct meaningful errors briefly and specifically.
- Ignore harmless capitalization, punctuation, spacing, formatting, and obvious minor typing slips when they do not change meaning.
- Do not treat a valid alternative expression as an error just because it differs from the model.
- Do not turn practice into a grammar lesson.
- Do not output JSON, control markers, Markdown, or meta-commentary.
"""


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


def _stream_stage_response(*, user_id: int, request: StageChatRequest):
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

        explanation_language = (
            getattr(user, "tutor_explanation_language_mode", None)
            or user.native_language
            or "en"
        )
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

        rows = [] if control_message else _raw_history(db, conversation_id)
        completed = _completed_target_orders(rows)
        history = _history_messages(rows, request.stage)

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

            current_target = _target_by_order(targets, current_order)
            if current_target is None:
                yield _sse("error", {"message": "Current lesson target not found"})
                return

            phase = "TEACH" if control_message or _target_needs_teaching(rows, current_order) else "EVALUATE"
            system_prompt = _teaching_system_prompt(
                lesson,
                profile,
                current_target,
                current_order,
                explanation_language,
                phase,
            )
        else:
            current_order = None
            system_prompt = _practice_system_prompt(
                lesson,
                profile,
                targets,
                explanation_language,
                _practice_context(db, lesson.id),
            )

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        if control_message:
            messages.append(
                {
                    "role": "user",
                    "content": "Start the current target now. Follow the TEACH phase before asking for an answer.",
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": request.message[:MAX_LEARNER_MESSAGE_CHARS],
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

            # A new target can never be completed on its first teaching turn.
            if phase == "TEACH":
                target_completed = False
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
