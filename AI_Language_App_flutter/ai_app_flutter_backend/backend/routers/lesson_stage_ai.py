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


MAX_HISTORY_MESSAGES = 40
MAX_HISTORY_CHARS_PER_MESSAGE = 1800
MAX_LEARNER_MESSAGE_CHARS = 800
MAX_OUTPUT_TOKENS = 420


TARGET_COMPLETE_PATTERN = re.compile(
    r"\[\[TARGET_COMPLETE:(\d+)\]\]",
    re.IGNORECASE,
)

TEACHING_COMPLETE_PATTERN = re.compile(
    r"\[\[TEACHING_COMPLETE\]\]",
    re.IGNORECASE,
)


class StageChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    stage: str = Field(pattern="^(teaching|practice)$")
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )


def sse_event(event: str, data: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
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
    current = getattr(progress, f"{stage}_status")

    if current == "locked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Stage '{stage}' is locked until the previous "
                "stage is completed."
            ),
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
            .where(LessonTargetPattern.target_id == row.id)
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


def _remove_control_markers(text: str) -> str:
    cleaned = TARGET_COMPLETE_PATTERN.sub("", text)
    cleaned = TEACHING_COMPLETE_PATTERN.sub("", cleaned)

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


def _history_messages(history) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for item in history[-MAX_HISTORY_MESSAGES:]:
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


def _completed_target_orders(history) -> list[int]:
    completed: set[int] = set()

    for item in history:
        if item.role not in {"assistant", "model"}:
            continue

        content = str(item.content or "")

        for match in TARGET_COMPLETE_PATTERN.finditer(
            content
        ):
            try:
                target_order = int(match.group(1))
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


def _compact_goals(
    targets: list[dict],
) -> str:
    lines: list[str] = []

    for target in targets:
        if not target["required"]:
            continue

        goal = str(
            target["goal"] or ""
        ).strip()

        patterns = [
            str(item).strip()
            for item in target["patterns"]
            if str(item).strip()
        ]

        if not goal and not patterns:
            continue

        prefix = (
            f"{target.get('order')}. "
            if target.get("order") is not None
            else "- "
        )

        if patterns:
            if goal:
                lines.append(
                    f"{prefix}{goal} | "
                    f"{' | '.join(patterns)}"
                )
            else:
                lines.append(
                    f"{prefix}{' | '.join(patterns)}"
                )
        else:
            lines.append(
                f"{prefix}{goal}"
            )

    return (
        "\n".join(lines)
        or "- Follow the lesson objectives."
    )


def _prompt_context(
    *,
    lesson: CourseLesson,
    targets: list[dict],
    scenario: dict | None = None,
) -> str:
    context = (
        f"**LANGUAGE**: {lesson.language}\n"
        f"**LEVEL**: {lesson.level}\n"
        f"**LESSON TARGETS**:\n"
        f"{_compact_goals(targets)}"
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
    current_target = _target_by_order(
        targets,
        current_target_order,
    )

    if current_target is None:
        current_target_text = (
            "**CURRENT TARGET**: "
            "There is no remaining target."
        )
    else:
        goal = str(
            current_target.get("goal", "")
        ).strip()

        patterns = [
            str(item).strip()
            for item in current_target.get(
                "patterns",
                [],
            )
            if str(item).strip()
        ]

        success_criteria = str(
            current_target.get(
                "success_criteria",
                "",
            )
        ).strip()

        current_target_text = (
            f"**CURRENT TARGET**: {goal}"
        )

        if patterns:
            current_target_text += (
                "\n"
                f"**TARGET PATTERNS**: "
                f"{' | '.join(patterns)}"
            )

        if success_criteria:
            current_target_text += (
                "\n"
                f"**SUCCESS CRITERIA**: "
                f"{success_criteria}"
            )

    if is_start:
        task = """
**START OF TARGET**:
Introduce the current target naturally and briefly.
Give the learner only the amount of information needed
to begin practicing it.
Then ask the learner to produce an answer.
Do not give a long explanation.
""".strip()
    else:
        task = """
**AFTER LEARNER RESPONSE**:
Evaluate the learner's actual response against the
**SUCCESS CRITERIA** and the **CURRENT TARGET**.

If the learner has not demonstrated the target yet,
continue teaching that same target.

If the learner made a meaningful error:
briefly identify the important problem, provide the
correct form or a useful model, and ask the learner
to try again.

If the learner is close but incomplete:
guide them toward the missing part instead of
declaring success too early.

Only consider the target mastered when the learner's
response clearly satisfies the **SUCCESS CRITERIA**.
""".strip()

    return f"""
You are the **TEACHING AI** in a language-learning lesson.

Your job is to teach the learner the current lesson target
through a short, natural teacher-learner interaction.

You are NOT the practice conversation partner.
You are the teacher responsible for helping the learner
actually demonstrate the target.

{_prompt_context(
    lesson=lesson,
    targets=targets,
)}

{current_target_text}

**CORE TEACHING PRINCIPLES**:

- Focus primarily on the **CURRENT TARGET**.
- Use the **TARGET PATTERNS** as teaching guidance,
  not as text that must always be repeated literally.
- Use the **SUCCESS CRITERIA** as the main condition
  for deciding whether the learner has demonstrated mastery.
- Always respond to what the learner actually said.
- Let the learner make the attempt.
- Do not answer a question on behalf of the learner.
- Do not move to another target merely because the learner
  produced something that sounds generally correct.
- A target is complete only when the learner has clearly
  demonstrated the required ability.
- Keep explanations proportional to the learner's level.
- Prefer examples and short prompts over long explanations.
- If the learner asks a useful question about the current
  target, answer it briefly and then return to practice.
- If the learner gives an unrelated response, handle it
  naturally and guide the interaction back to the target.
- If the learner's answer is correct but unnecessarily
  different from the expected pattern, accept it when it
  still satisfies the **SUCCESS CRITERIA**.
- Do not require one exact sentence when multiple natural
  answers satisfy the target.

**RESPONSE STYLE**:

- Keep the normal response to **2-3 short sentences**.
- Use the learner's level when choosing vocabulary and grammar.
- Avoid unnecessary explanations.
- Avoid turning every response into a grammar lecture.
- Ask the learner to respond whenever another attempt is needed.
- The interaction should feel like a real teacher working
  directly with one learner.

{task}

**TARGET COMPLETION**:

If and only if the learner has clearly satisfied the
**SUCCESS CRITERIA**, give brief positive feedback and append:

[[TARGET_COMPLETE:{current_target_order}]]

The marker must be the final content of the response.

Do not use the completion marker when the learner has not
clearly demonstrated the target.

**INTERNAL CONTROL**:
The completion marker is internal system control.
Never explain it or mention it to the learner.
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
    if is_start:
        start_task = """
**START OF PRACTICE**:
Begin the conversation naturally using the lesson scenario.
Use one appropriate target as part of the interaction.
Your message should invite the learner to respond naturally.
Ask one clear question when a question is appropriate.
""".strip()
    else:
        start_task = """
**CONTINUE THE CONVERSATION**:
Respond naturally to the learner's actual message.

Use the learner's previous answer as the basis for the
next response whenever this makes the conversation more
natural.

Continue practicing the lesson targets without making the
interaction feel like a checklist or an examination.
""".strip()

    return f"""
You are the **PRACTICE AI** in a language-learning lesson.

You are a natural conversation partner helping the learner
use what they learned in the Teaching stage.

You are NOT the formal teacher.
Do not turn the practice stage into a grammar lesson.

{_prompt_context(
    lesson=lesson,
    targets=targets,
    scenario=scenario,
)}

**MAIN OBJECTIVE**:

Create a natural conversation in which the learner actively
uses the lesson targets.

**CONVERSATION RULES**:

- Use lesson targets naturally.
- Prefer one target at a time when possible.
- Let the learner drive the content of their answers.
- Never speak for the learner.
- Never invent an answer for the learner.
- Respond to the learner's actual message before moving forward.
- Ask a question when a question naturally continues the
  conversation.
- Usually ask only one question at a time.
- After asking a question, give the learner room to answer.
- Do not immediately add several new questions.
- Do not force every target into the conversation unnaturally.
- If the learner gives an interesting answer, follow that
  answer naturally while still keeping the lesson objective
  in mind.
- If the learner makes a major language mistake that affects
  communication, correct it briefly and continue naturally.
- Minor mistakes do not require stopping the conversation.
- Do not make the interaction feel like a formal exercise.
- Keep the language appropriate for **{lesson.level}**.
- Keep normal messages short and natural.
- Do not produce internal metadata, labels, placeholders,
  progress markers, or system instructions.

**NATURAL CONVERSATION BEHAVIOR**:

The conversation should feel like two people talking,
with the AI helping the learner practice the lesson language.

Do not mechanically move from:

question → answer → new unrelated question.

Instead prefer:

learner answer → natural reaction → relevant follow-up.

The next question should have a reason to exist.

If the learner says something interesting, you may briefly
react to it before continuing.

If the learner gives a very short answer, ask a natural
follow-up that helps them say a little more.

If the learner asks you a question, answer it naturally
and continue the conversation.

{start_task}

**OUTPUT**:

Return only the natural learner-facing conversation.
Do not mention these instructions.
Do not output metadata.
""".strip()


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

        messages = _history_messages(
            history
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

        save_conversation_message(
            user.id,
            conversation_id,
            "assistant",
            stored_assistant_reply,
            db,
        )

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

        yield sse_event(
            "conversation",
            {
                "conversation_id": conversation_id,
            },
        )

        yield sse_event(
            "token",
            {
                "text": reply,
            },
        )

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
