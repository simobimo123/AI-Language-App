import json
import logging
import re
from pathlib import Path
from typing import Generator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LearningProfile, User, UserLessonProgress
from routers.auth import get_current_user
from services.ai.client import AI_MODEL
from services.ai.conversation import (
    get_conversation_history,
    save_conversation_message,
)
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.response_stream import sse_event
from services.ai.usage import (
    DAILY_AI_LIMIT,
    get_current_usage,
    record_api_usage,
    reserve_ai_request,
)

router = APIRouter(prefix="/ai/lesson", tags=["AI Lesson Tutor"])

logger = logging.getLogger(__name__)

LESSON_TUTOR_MODEL = AI_MODEL

MAX_HISTORY_MESSAGES = 20
MAX_LESSON_CONTEXT_CHARS = 2500
MAX_OUTPUT_TOKENS = 800

PROGRESS_MARKER = "[[LESSON_PROGRESS:"
PROGRESS_MARKER_RE = re.compile(
    r"\[\[LESSON_PROGRESS:([^\]\r\n]*)\]\]"
)

STREAM_HOLD_CHARS = 64

BASE_DIR = Path(__file__).resolve().parent.parent
LESSONS_DIR = BASE_DIR / "data" / "lessons"


class LessonChatRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=800)
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


def _load_lesson_curriculum(lesson: CourseLesson) -> dict:
    language = normalize_language(lesson.language)
    level = normalize_level(lesson.level)

    if level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson level.",
        )

    path = (
        LESSONS_DIR
        / language
        / level
        / f"lesson_{lesson.lesson_order:02d}.json"
    )

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson curriculum is not available.",
        )

    try:
        data = json.loads(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception(
            "Failed to load lesson curriculum: %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson curriculum could not be loaded.",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid lesson curriculum format.",
        )

    return data


def _normalize_target_role(role: str) -> str:
    role = str(role or "").strip().lower()

    if role in {"assistant", "assistant_character"}:
        return "assistant"

    if role == "learner":
        return "learner"

    if role == "either":
        return "either"

    return "either"


def _lesson_target_sentences(
    curriculum: dict,
) -> list[dict[str, str]]:
    """
    Build one ordered list of conversation milestones.

    Supported formats:

    1. New scene-based format:
       conversation.scenes[].flow[]

    2. Intermediate path format:
       conversation.path[]

    3. Legacy formats:
       key_sentences / sections
    """

    conversation = curriculum.get("conversation")

    # ------------------------------------------------------------------
    # NEW FORMAT: conversation.scenes
    # ------------------------------------------------------------------
    if isinstance(conversation, dict):
        scenes = conversation.get("scenes")

        if isinstance(scenes, list) and scenes:
            result: list[dict[str, str]] = []
            seen_ids: set[str] = set()

            for scene_index, scene in enumerate(scenes, start=1):
                if not isinstance(scene, dict):
                    continue

                scene_id = str(
                    scene.get(
                        "id",
                        f"scene_{scene_index}",
                    )
                ).strip()

                scene_context = str(
                    scene.get("context", "")
                ).strip()

                scene_purpose = str(
                    scene.get("purpose", "")
                ).strip()

                scene_character = str(
                    scene.get("character", "")
                ).strip()

                flow = scene.get("flow")

                if not isinstance(flow, list):
                    continue

                for flow_index, item in enumerate(
                    flow,
                    start=1,
                ):
                    if not isinstance(item, dict):
                        continue

                    target = str(
                        item.get(
                            "target_pattern",
                            item.get(
                                "target",
                                item.get(
                                    "sentence",
                                    item.get(
                                        "text",
                                        "",
                                    ),
                                ),
                            ),
                        )
                    ).strip()

                    if not target:
                        continue

                    target_id = str(
                        item.get(
                            "id",
                            f"{scene_id}_{flow_index}",
                        )
                    ).strip()

                    if not target_id:
                        target_id = f"{scene_id}_{flow_index}"

                    if target_id in seen_ids:
                        target_id = (
                            f"{scene_id}_{flow_index}_{len(result)}"
                        )

                    if target_id in seen_ids:
                        continue

                    role = _normalize_target_role(
                        str(item.get("role", "either"))
                    )

                    speaker = str(
                        item.get(
                            "speaker",
                            "",
                        )
                    ).strip()

                    goal = str(
                        item.get(
                            "goal",
                            "",
                        )
                    ).strip()

                    action = str(
                        item.get(
                            "action",
                            "",
                        )
                    ).strip()

                    item_context = str(
                        item.get(
                            "context",
                            "",
                        )
                    ).strip()

                    context_parts: list[str] = []

                    if scene_context:
                        context_parts.append(
                            f"Scene context: {scene_context}"
                        )

                    if scene_purpose:
                        context_parts.append(
                            f"Scene purpose: {scene_purpose}"
                        )

                    if scene_character:
                        context_parts.append(
                            f"Scene character: {scene_character}"
                        )

                    if goal:
                        context_parts.append(
                            f"Goal: {goal}"
                        )

                    if action:
                        context_parts.append(
                            f"Action: {action}"
                        )

                    if item_context:
                        context_parts.append(
                            f"Target context: {item_context}"
                        )

                    context = " ".join(context_parts)

                    seen_ids.add(target_id)

                    result.append(
                        {
                            "id": target_id,
                            "sentence": target,
                            "role": role,
                            "context": context,
                            "scene_id": scene_id,
                            "speaker": speaker,
                        }
                    )

            if result:
                return result

        # ------------------------------------------------------------------
        # INTERMEDIATE FORMAT: conversation.path
        # ------------------------------------------------------------------
        raw_path = conversation.get("path")

        if isinstance(raw_path, list) and raw_path:
            result: list[dict[str, str]] = []
            seen_ids: set[str] = set()

            for index, item in enumerate(
                raw_path,
                start=1,
            ):
                if not isinstance(item, dict):
                    continue

                sentence = str(
                    item.get(
                        "target",
                        item.get(
                            "sentence",
                            item.get(
                                "text",
                                "",
                            ),
                        ),
                    )
                ).strip()

                if not sentence:
                    continue

                sentence_id = str(
                    item.get(
                        "id",
                        f"p{index}",
                    )
                ).strip()

                if not sentence_id:
                    sentence_id = f"p{index}"

                if sentence_id in seen_ids:
                    sentence_id = f"p{index}"

                if sentence_id in seen_ids:
                    continue

                role = _normalize_target_role(
                    str(
                        item.get(
                            "role",
                            "either",
                        )
                    )
                )

                context = str(
                    item.get(
                        "context",
                        "",
                    )
                ).strip()

                speaker = str(
                    item.get(
                        "speaker",
                        "",
                    )
                ).strip()

                seen_ids.add(sentence_id)

                result.append(
                    {
                        "id": sentence_id,
                        "sentence": sentence,
                        "role": role,
                        "context": context,
                        "scene_id": "",
                        "speaker": speaker,
                    }
                )

            if result:
                return result

    # ------------------------------------------------------------------
    # LEGACY FORMAT
    # ------------------------------------------------------------------

    raw = curriculum.get("key_sentences", [])

    expected_learner_responses: list[str] = []

    sections = curriculum.get("sections", [])

    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue

            values = section.get(
                "expected_learner_responses",
                [],
            )

            if isinstance(values, list):
                expected_learner_responses.extend(
                    str(value).strip()
                    for value in values
                    if isinstance(value, str)
                    and value.strip()
                )

    if not isinstance(raw, list) or not raw:
        collected: list[dict[str, str]] = []

        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict):
                    continue

                values = section.get(
                    "target_sentences",
                    [],
                )

                if not isinstance(values, list):
                    continue

                for value in values:
                    if (
                        isinstance(value, str)
                        and value.strip()
                    ):
                        collected.append(
                            {
                                "sentence": value.strip()
                            }
                        )

        raw = collected

    def looks_like_learner_response(
        sentence: str,
    ) -> bool:
        normalized_sentence = (
            re.sub(
                r"\s+",
                " ",
                sentence.strip().lower(),
            )
            .rstrip(".!?。！？")
        )

        for pattern in expected_learner_responses:
            normalized_pattern = (
                re.sub(
                    r"\s+",
                    " ",
                    pattern.strip().lower(),
                )
                .rstrip(".!?。！？")
            )

            if "..." in normalized_pattern:
                prefix, suffix = normalized_pattern.split(
                    "...",
                    1,
                )

                if (
                    normalized_sentence.startswith(
                        prefix.strip()
                    )
                    and normalized_sentence.endswith(
                        suffix.strip()
                    )
                ):
                    return True

            elif normalized_sentence == normalized_pattern:
                return True

        return False

    result: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_sentences: set[str] = set()

    for index, item in enumerate(
        raw,
        start=1,
    ):
        if isinstance(item, str):
            sentence = item.strip()
            explicit_id = ""

            role = (
                "learner"
                if looks_like_learner_response(sentence)
                else "assistant"
            )

        elif isinstance(item, dict):
            sentence = str(
                item.get(
                    "sentence",
                    item.get(
                        "text",
                        "",
                    ),
                )
            ).strip()

            explicit_id = str(
                item.get(
                    "id",
                    "",
                )
            ).strip()

            role = str(
                item.get(
                    "role",
                    "",
                )
            ).strip().lower()

            if role not in {
                "assistant",
                "learner",
                "either",
            }:
                role = (
                    "learner"
                    if looks_like_learner_response(sentence)
                    else "assistant"
                )

        else:
            continue

        if (
            not sentence
            or sentence in seen_sentences
        ):
            continue

        sentence_id = (
            explicit_id
            or str(index)
        )

        if sentence_id in seen_ids:
            sentence_id = str(index)

        if sentence_id in seen_ids:
            continue

        seen_ids.add(sentence_id)
        seen_sentences.add(sentence)

        result.append(
            {
                "id": sentence_id,
                "sentence": sentence,
                "role": role,
                "context": "",
                "scene_id": "",
                "speaker": "",
            }
        )

    return result


def _lesson_characters(
    curriculum: dict,
) -> list[dict[str, str]]:
    conversation = curriculum.get("conversation")

    if not isinstance(conversation, dict):
        return []

    raw_characters = conversation.get(
        "characters",
        [],
    )

    if not isinstance(raw_characters, list):
        return []

    characters: list[dict[str, str]] = []

    for item in raw_characters:
        if not isinstance(item, dict):
            continue

        character_id = str(
            item.get(
                "id",
                "",
            )
        ).strip()

        character_type = str(
            item.get(
                "type",
                "",
            )
        ).strip()

        name = str(
            item.get(
                "name",
                "",
            )
        ).strip()

        description = str(
            item.get(
                "description",
                "",
            )
        ).strip()

        if not (
            character_id
            or character_type
            or name
            or description
        ):
            continue

        characters.append(
            {
                "id": character_id,
                "type": character_type,
                "name": name,
                "description": description,
            }
        )

    return characters


def _lesson_scenes_context(
    curriculum: dict,
) -> list[dict[str, object]]:
    conversation = curriculum.get("conversation")

    if not isinstance(conversation, dict):
        return []

    raw_scenes = conversation.get(
        "scenes",
        [],
    )

    if not isinstance(raw_scenes, list):
        return []

    scenes: list[dict[str, object]] = []

    for scene in raw_scenes:
        if not isinstance(scene, dict):
            continue

        scene_id = str(
            scene.get(
                "id",
                "",
            )
        ).strip()

        purpose = str(
            scene.get(
                "purpose",
                "",
            )
        ).strip()

        context = str(
            scene.get(
                "context",
                "",
            )
        ).strip()

        character = str(
            scene.get(
                "character",
                "",
            )
        ).strip()

        transition = scene.get(
            "transition",
            {},
        )

        transition_data: dict[str, object] = {}

        if isinstance(transition, dict):
            transition_data = {
                "condition": str(
                    transition.get(
                        "condition",
                        "",
                    )
                ).strip(),
                "next_scene": str(
                    transition.get(
                        "next_scene",
                        "",
                    )
                ).strip(),
                "style": str(
                    transition.get(
                        "style",
                        "",
                    )
                ).strip(),
                "instruction": str(
                    transition.get(
                        "instruction",
                        "",
                    )
                ).strip(),
            }

        scenes.append(
            {
                "id": scene_id,
                "purpose": purpose,
                "context": context,
                "character": character,
                "transition": transition_data,
            }
        )

    return scenes


def _lesson_context(
    data: dict,
) -> str:
    """
    Build compact context from the scene-based and legacy lesson formats.
    """

    metadata = data.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    title = str(
        data.get(
            "title",
            metadata.get(
                "title",
                "",
            ),
        )
    ).strip()

    objective = str(
        data.get(
            "objective",
            metadata.get(
                "objective",
                "",
            ),
        )
    ).strip()

    conversation = data.get(
        "conversation",
        {},
    )

    mode = ""

    if isinstance(conversation, dict):
        mode = str(
            conversation.get(
                "mode",
                "",
            )
        ).strip()

    characters = _lesson_characters(data)

    scenes = _lesson_scenes_context(data)

    section_context: dict[str, object] = {}

    sections = data.get(
        "sections",
        [],
    )

    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue

            section_type = str(
                section.get(
                    "type",
                    "",
                )
            ).lower()

            if section_type in {
                "test",
                "assessment",
                "review",
                "end_test",
            }:
                continue

            section_context = {
                "title": str(
                    section.get(
                        "title",
                        "",
                    )
                ).strip(),
                "objective": str(
                    section.get(
                        "objective",
                        "",
                    )
                ).strip(),
                "scenario": str(
                    section.get(
                        "scenario",
                        "",
                    )
                ).strip(),
                "focus": section.get(
                    "focus",
                    [],
                ),
            }

            break

    selected: dict[str, object] = {
        "topic": title,
        "objective": objective,
        "conversation_mode": mode,
    }

    if characters:
        selected["characters"] = characters

    if scenes:
        selected["scenes"] = scenes

    if section_context:
        selected["legacy_focus"] = section_context

    text = json.dumps(
        selected,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return text[:MAX_LESSON_CONTEXT_CHARS]


def _get_or_create_practice_progress(
    user_id: int,
    profile_id: int,
    lesson_id: int,
    conversation_id: str,
    db: Session,
) -> UserLessonProgress:
    progress = db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = UserLessonProgress(
            user_id=user_id,
            learning_profile_id=profile_id,
            lesson_id=lesson_id,
            practice_state={
                "conversation_id": conversation_id,
                "practiced_sentence_ids": [],
            },
        )

        db.add(progress)
        db.flush()

        return progress

    state = (
        progress.practice_state
        if isinstance(
            progress.practice_state,
            dict,
        )
        else {}
    )

    if state.get("conversation_id") != conversation_id:
        progress.practice_state = {
            "conversation_id": conversation_id,
            "practiced_sentence_ids": [],
        }

    return progress


def _practiced_sentence_ids(
    progress: UserLessonProgress,
) -> set[str]:
    state = (
        progress.practice_state
        if isinstance(
            progress.practice_state,
            dict,
        )
        else {}
    )

    raw = state.get(
        "practiced_sentence_ids",
        [],
    )

    if not isinstance(raw, list):
        return set()

    return {
        str(value).strip()
        for value in raw
        if str(value).strip()
    }


def _update_practice_progress(
    *,
    progress: UserLessonProgress,
    conversation_id: str,
    completed_ids: set[str],
    ordered_ids: list[str],
) -> set[str]:
    """
    Apply only a contiguous prefix of the curriculum.

    A later target can never be marked complete while an earlier
    target remains unfinished.
    """

    ordered_set = set(ordered_ids)

    current = (
        _practiced_sentence_ids(progress)
        & ordered_set
    )

    completed = (
        completed_ids
        & ordered_set
    )

    for target_id in ordered_ids:
        if target_id in current:
            continue

        if target_id in completed:
            current.add(target_id)
            continue

        break

    progress.practice_state = {
        "conversation_id": conversation_id,
        "practiced_sentence_ids": [
            target_id
            for target_id in ordered_ids
            if target_id in current
        ],
    }

    return current


def _extract_progress_marker(
    text: str,
) -> tuple[str, set[str]]:
    matches = list(
        PROGRESS_MARKER_RE.finditer(text)
    )

    if not matches:
        return text.strip(), set()

    match = matches[-1]

    raw_ids = match.group(1)

    ids = {
        value.strip()
        for value in raw_ids.split(",")
        if value.strip()
    }

    cleaned = PROGRESS_MARKER_RE.sub(
        "",
        text,
    ).strip()

    return cleaned, ids


def _remove_exact_duplicate_response(
    text: str,
) -> str:
    """
    Remove accidental complete-response duplication while
    preserving legitimate repeated wording.
    """

    cleaned = re.sub(
        r"[\u200b\u200c\u200d\ufeff]",
        "",
        text,
    ).strip()

    if not cleaned:
        return cleaned

    match = re.fullmatch(
        r"(.+?)\s+\1",
        cleaned,
        flags=re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    normalized = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    if (
        len(normalized) >= 4
        and len(normalized) % 2 == 0
    ):
        half = len(normalized) // 2

        if (
            normalized[:half].rstrip()
            == normalized[half:].lstrip()
        ):
            return normalized[:half].strip()

    sentence_match = re.fullmatch(
        r"(.+?[.!?。！？])\s+\1",
        cleaned,
        flags=re.DOTALL,
    )

    if sentence_match:
        return sentence_match.group(1).strip()

    return cleaned


def _lesson_completion(
    curriculum: dict,
    progress: UserLessonProgress,
) -> tuple[bool, int, int]:
    target_ids = {
        item["id"]
        for item in _lesson_target_sentences(
            curriculum
        )
    }

    practiced_ids = (
        _practiced_sentence_ids(progress)
        & target_ids
    )

    if not target_ids:
        return (
            False,
            len(practiced_ids),
            0,
        )

    return (
        target_ids.issubset(practiced_ids),
        len(practiced_ids),
        len(target_ids),
    )


def _build_target_tracking_context(
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    """
    Return the current actionable milestone and compact
    remaining scene/path information.
    """

    targets = _lesson_target_sentences(
        curriculum
    )

    practiced = _practiced_sentence_ids(
        progress
    )

    remaining = [
        item
        for item in targets
        if item["id"] not in practiced
    ]

    if not remaining:
        return json.dumps(
            {
                "next_target": None,
                "remaining_targets": [],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    next_target = remaining[0]

    compact_remaining: list[dict[str, str]] = []

    for item in remaining:
        compact_item = {
            "id": item["id"],
            "role": item["role"],
            "target": item["sentence"],
            "context": item.get(
                "context",
                "",
            ),
        }

        scene_id = item.get(
            "scene_id",
            "",
        )

        speaker = item.get(
            "speaker",
            "",
        )

        if scene_id:
            compact_item["scene_id"] = scene_id

        if speaker:
            compact_item["speaker"] = speaker

        compact_remaining.append(
            compact_item
        )

    return json.dumps(
        {
            "next_target": {
                "id": next_target["id"],
                "role": next_target["role"],
                "target": next_target["sentence"],
                "context": next_target.get(
                    "context",
                    "",
                ),
                "scene_id": next_target.get(
                    "scene_id",
                    "",
                ),
                "speaker": next_target.get(
                    "speaker",
                    "",
                ),
            },
            "remaining_targets": compact_remaining,
            "ordered_path": True,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _build_system_instruction(
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    progress: UserLessonProgress,
) -> str:
    context = _lesson_context(
        curriculum
    )

    targets = _build_target_tracking_context(
        curriculum,
        progress,
    )

    teacher_instructions = curriculum.get(
        "teacher_instructions",
        {},
    )

    if not isinstance(
        teacher_instructions,
        dict,
    ):
        teacher_instructions = {}

    start_message = str(
        teacher_instructions.get(
            "start_message",
            "",
        )
    ).strip()

    legacy_start_rule = ""

    if start_message:
        legacy_start_rule = f"""
LEGACY LESSON START INSTRUCTION:

{start_message}
"""

    return f"""You are the AI conversation partner for one language-learning lesson.

Language: {target_language}

Learner native language: {native_language}

CEFR level: {level}

LESSON CURRICULUM CONTEXT

{context}

CURRENT CONVERSATION STATE

{targets}

The curriculum above is the source of truth for the lesson.

The conversation must feel like ONE continuous real-life interaction.

The curriculum contains scenes and conversation milestones. These are internal instructions. The learner must never see them.

STRICT SCENE AND PATH RULES

1. Always work on the FIRST unfinished target only.

2. Never jump to a later target.

3. Never mark or assume completion of a later target while the current target is unfinished.

4. The current target is the most important instruction for the current response.

5. Use the current scene context to make the conversation natural.

6. Do not introduce a new person unless that person exists in the lesson curriculum or is explicitly introduced by the learner.

7. If the curriculum introduces a character such as Thomas or Anna, keep that character's identity consistent.

8. Never confuse a curriculum character with the learner.

9. Never confuse the tutor with the learner.

10. Never invent the learner's name, location, family, friends, or personal information.

11. The learner's personal information comes only from what the learner actually says.

12. The tutor's personal information comes only from what the tutor itself says.

13. If a curriculum character says something, that information belongs to that character.

14. If the learner says "Ich heiße X", X is the learner's name.

15. If the learner says "Ich wohne in X", X is the learner's residence.

16. If the tutor says "Ich heiße X", X is the tutor's name.

17. If the tutor says "Ich wohne in X", X is the tutor's residence.

18. If a character such as Thomas says "Ich heiße Thomas", Thomas is Thomas. This does NOT make Thomas the learner or tutor.

19. Do not ask the learner again for information that has already been established.

20. If the learner gives a new explicit personal fact, use the newest fact.

21. If the learner changes or corrects their name or location, use the newest explicit statement.

SCENE CONTINUITY

22. Every new person or topic must have a natural reason to appear.

23. Follow the transition instructions of the current scene.

24. Do not jump from one character to an unrelated character.

25. Do not create unrelated stories.

26. Do not introduce random names such as Tom, Anna, Maria, etc. unless they are in the curriculum or the learner introduced them.

27. If the current scene is about Thomas, stay with Thomas until the scene's required goal is completed.

28. If the next scene introduces Anna, transition naturally from the current conversation to Anna.

29. When the curriculum says that the learner should ask a character a question, make that request naturally. Do not present it as a numbered exercise.

30. When a character is supposed to answer, speak as that character when appropriate.

31. Do not invent facts about curriculum characters beyond what the curriculum establishes.

TARGET ROLE RULES

32. If the next target has role "assistant", naturally produce that target in your response.

33. If the next target has role "learner", do NOT pretend the learner already said it.

34. For a learner target, naturally ask, prompt, or create the situation that makes the learner produce it.

35. If the next target has role "assistant", the tutor may add a very short natural transition before or after the target.

36. If the next target has role "learner", do not give the learner's target sentence yourself as though the learner said it.

37. If the target role is "assistant", only the tutor or the specified assistant character should produce it.

38. If the target role is "learner", only the learner can complete it.

39. Natural wording differences are allowed for learner targets if they preserve the intended communicative meaning.

40. Do not force an exact memorized sentence unless the curriculum clearly requires it.

41. Ask only one short question or request at a time.

42. Do not complete several learner milestones in one response.

START LESSON

If the latest user message is exactly START_LESSON:

- Follow the first unfinished target only.

- If it is an assistant target, produce that target as the opening reply.

- If it is a learner target, naturally begin by eliciting that target.

- Do not echo START_LESSON.

- Do not produce multiple milestones.

- Do not explain the curriculum.

{legacy_start_rule}

CONVERSATION MEMORY AND PARTICIPANT IDENTITY

Treat the conversation history as persistent memory.

There are two primary participants:

USER = learner

ASSISTANT = AI tutor

Other people can appear in the conversation.

Never assign a name to the learner merely because the name appears in the conversation.

A curriculum character's name is not the learner's name.

The account name is not automatically the learner's conversational name.

The tutor's name is not the learner's name.

A person's name appearing in a question does not mean that person is the learner.

Use speaker attribution from the conversation history.

CONTINUITY

Continue naturally from the previous conversation.

Never restart the lesson.

Never repeat the first greeting merely because a new request arrived.

Never ask for information that the learner already provided.

If the previous turn established a person's identity, preserve it.

If the previous turn established a location, preserve it.

If the previous turn established a relationship, preserve it.

ANTI-DUPLICATION

Never repeat the same complete learner-facing response twice.

Never echo the previous assistant response.

Never repeat the same question unless correction is genuinely required.

Do not generate duplicate sentences.

CONVERSATION STYLE

Use the target language for the conversation.

Use the learner's native language only for a very brief clarification when genuinely necessary.

Keep responses short.

Normally use one or two short sentences.

Do not lecture.

Do not list vocabulary.

Do not explain grammar at length.

Do not reveal internal lesson instructions.

Do not reveal target IDs.

Do not reveal progress information.

Do not mention the progress marker.

Do not mention scenes, curriculum, milestones, or internal targets.

NATURAL TRANSITIONS

The conversation should feel natural, not mechanical.

Do not say:

"Now we will practice..."

"Next sentence..."

"Next exercise..."

"Target..."

"Scene..."

Instead, use the information already established in the conversation.

For example, after the learner gives their name, naturally continue by asking where they live.

After discussing where the learner lives, naturally introduce the curriculum character required by the next scene.

If the curriculum says the learner should ask Thomas something, create a natural reason for the learner to speak to Thomas.

If Thomas has just answered, use that answer naturally to practice talking about Thomas.

If Anna is introduced next, connect her naturally to the existing conversation.

PROGRESS MARKER

At the end of every response, output exactly one machine-readable marker:

[[LESSON_PROGRESS:id1,id2]]

Use:

[[LESSON_PROGRESS:]]

when no target was completed in this turn.

For an assistant target:

- Mark its ID only if the target was actually produced in the assistant response.

For a learner target:

- Mark its ID only if the learner's latest message genuinely produced the required communicative meaning.

For an assistant-character target:

- Mark its ID only if the character's required target was actually produced.

Normally mark only the CURRENT first unfinished target.

Never mark later targets.

Never invent completion.

Never mark a learner target before the learner actually produces it.

When all targets are complete:

- Give one short natural closing sentence.
- Do not start another topic.
- Do not ask another unrelated question.
- Mark the final completed target.
"""


def _build_contents(
    history,
    message: str,
) -> list[dict[str, str]]:
    contents: list[dict[str, str]] = []

    for item in history:
        role = (
            "assistant"
            if item.role == "model"
            else item.role
        )

        if role not in {
            "user",
            "assistant",
            "system",
        }:
            role = "user"

        contents.append(
            {
                "role": role,
                "content": item.content,
            }
        )

    contents.append(
        {
            "role": "user",
            "content": message,
        }
    )

    return contents


def _completed_lesson_stream(
    conversation_id: str,
    practiced_count: int,
    target_count: int,
) -> Generator[str, None, None]:
    yield sse_event(
        "done",
        {
            "conversation_id": conversation_id,
            "completed": True,
            "conversation_completed": True,
            "practiced_sentences": practiced_count,
            "target_sentences": target_count,
        },
    )


def _stream_lesson_response(
    *,
    request: LessonChatRequest,
    user_id: int,
    db: Session,
    native_language: str,
    target_language: str,
    level: str,
    curriculum: dict,
    conversation_id: str,
    profile_id: int,
) -> Generator[str, None, None]:
    try:
        progress = _get_or_create_practice_progress(
            user_id,
            profile_id,
            request.lesson_id,
            conversation_id,
            db,
        )

        history = get_conversation_history(
            user_id=user_id,
            conversation_id=conversation_id,
            max_messages=MAX_HISTORY_MESSAGES,
            db=db,
        )

        system_instruction = _build_system_instruction(
            native_language,
            target_language,
            level,
            curriculum,
            progress,
        )

        messages = _build_contents(
            history,
            request.message,
        )

        full_text = ""

        usage = (
            0,
            0,
            0,
        )

        buffer = ""

        streamed_visible_text = ""

        for chunk in provider.stream_text(
            system_instruction=system_instruction,
            contents=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ):
            if isinstance(chunk, dict):
                text = str(
                    chunk.get(
                        "text",
                        "",
                    )
                    or ""
                )

                usage = (
                    chunk.get(
                        "usage",
                        usage,
                    )
                    or usage
                )

            else:
                text = str(
                    getattr(
                        chunk,
                        "text",
                        "",
                    )
                    or ""
                )

                chunk_usage = (
                    getattr(
                        chunk,
                        "prompt_tokens",
                        0,
                    )
                    or 0,
                    getattr(
                        chunk,
                        "completion_tokens",
                        0,
                    )
                    or 0,
                    getattr(
                        chunk,
                        "total_tokens",
                        0,
                    )
                    or 0,
                )

                if any(chunk_usage):
                    usage = chunk_usage

            if not text:
                continue

            full_text += text
            buffer += text

            marker_index = buffer.find(
                PROGRESS_MARKER
            )

            if marker_index >= 0:
                learner_text = buffer[
                    :marker_index
                ]

                buffer = ""

                if learner_text:
                    streamed_visible_text += (
                        learner_text
                    )

                    yield sse_event(
                        "token",
                        {
                            "text": learner_text
                        },
                    )

                continue

            if len(buffer) > STREAM_HOLD_CHARS:
                emit = buffer[
                    :-STREAM_HOLD_CHARS
                ]

                buffer = buffer[
                    -STREAM_HOLD_CHARS:
                ]

                if emit:
                    streamed_visible_text += emit

                    yield sse_event(
                        "token",
                        {
                            "text": emit
                        },
                    )

        cleaned_text, completed_ids = (
            _extract_progress_marker(
                full_text
            )
        )

        cleaned_text = (
            _remove_exact_duplicate_response(
                cleaned_text
            )
        )

        # Flush everything that was intentionally held back
        # during streaming.
        if cleaned_text.startswith(
            streamed_visible_text
        ):
            remaining_text = cleaned_text[
                len(streamed_visible_text):
            ]

            if remaining_text:
                yield sse_event(
                    "token",
                    {
                        "text": remaining_text
                    },
                )

        else:
            # Defensive fallback if the model's final text
            # differs from the streamed prefix.
            if cleaned_text:
                yield sse_event(
                    "token",
                    {
                        "text": cleaned_text
                    },
                )

        save_conversation_message(
            user_id,
            conversation_id,
            "user",
            request.message,
            db,
        )

        if cleaned_text:
            save_conversation_message(
                user_id,
                conversation_id,
                "assistant",
                cleaned_text,
                db,
            )

        ordered_targets = (
            _lesson_target_sentences(
                curriculum
            )
        )

        ordered_ids = [
            item["id"]
            for item in ordered_targets
        ]

        _update_practice_progress(
            progress=progress,
            conversation_id=conversation_id,
            completed_ids=completed_ids,
            ordered_ids=ordered_ids,
        )

        db.commit()

        try:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            if isinstance(
                usage,
                (tuple, list),
            ):
                if len(usage) >= 1:
                    prompt_tokens = usage[0]

                if len(usage) >= 2:
                    completion_tokens = usage[1]

                if len(usage) >= 3:
                    total_tokens = usage[2]

            record_api_usage(
                user_id=user_id,
                prompt_tokens=int(
                    prompt_tokens
                ),
                completion_tokens=int(
                    completion_tokens
                ),
                total_tokens=int(
                    total_tokens
                ),
                db=db,
                model=LESSON_TUTOR_MODEL,
            )

        except Exception:
            logger.exception(
                "Failed to record lesson AI usage."
            )

        completed, practiced_count, target_count = (
            _lesson_completion(
                curriculum,
                progress,
            )
        )

        yield sse_event(
            "done",
            {
                "conversation_id": conversation_id,
                "completed": completed,
                "conversation_completed": completed,
                "practiced_sentences": practiced_count,
                "target_sentences": target_count,
            },
        )

    except Exception as exc:
        logger.exception(
            "Lesson AI streaming failed: %s",
            exc,
        )

        # Roll back any uncommitted database state.
        try:
            db.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback lesson AI transaction."
            )

        yield sse_event(
            "error",
            {
                "message": str(exc)
            },
        )


@router.post("/chat")
def lesson_chat(
    request: LessonChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id
            == current_user.id
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning profile not found.",
        )

    lesson = db.execute(
        select(CourseLesson).where(
            CourseLesson.id
            == request.lesson_id
        )
    ).scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    if lesson.language != profile.language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Lesson language does not match "
                "the learning profile."
            ),
        )

    target_language = normalize_language(
        profile.language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    level = normalize_level(
        lesson.level
    )

    if level is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson level.",
        )

    curriculum = _load_lesson_curriculum(
        lesson
    )

    targets = _lesson_target_sentences(
        curriculum
    )

    if not targets:
        logger.error(
            "Lesson %s has no conversation targets. "
            "Curriculum keys=%s conversation_keys=%s",
            request.lesson_id,
            list(curriculum.keys()),
            (
                list(
                    curriculum.get(
                        "conversation",
                        {},
                    ).keys()
                )
                if isinstance(
                    curriculum.get(
                        "conversation",
                        {},
                    ),
                    dict,
                )
                else []
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Lesson conversation targets are empty. "
                "Check conversation.scenes or conversation.path."
            ),
        )

    conversation_id = (
        request.conversation_id
        or f"lesson_{uuid4()}"
    )

    progress = _get_or_create_practice_progress(
        current_user.id,
        profile.id,
        request.lesson_id,
        conversation_id,
        db,
    )

    completed, practiced_count, target_count = (
        _lesson_completion(
            curriculum,
            progress,
        )
    )

    if completed:
        db.commit()

        return StreamingResponse(
            _completed_lesson_stream(
                conversation_id,
                practiced_count,
                target_count,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    check_rate_limit(
        user_id=current_user.id
    )

    usage = get_current_usage(
        user_id=current_user.id,
        db=db,
    )

    if usage.request_count >= DAILY_AI_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI limit reached.",
        )

    reserve_ai_request(
        user_id=current_user.id,
        db=db,
    )

    return StreamingResponse(
        _stream_lesson_response(
            request=request,
            user_id=current_user.id,
            db=db,
            native_language=native_language,
            target_language=target_language,
            level=level,
            curriculum=curriculum,
            conversation_id=conversation_id,
            profile_id=profile.id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )