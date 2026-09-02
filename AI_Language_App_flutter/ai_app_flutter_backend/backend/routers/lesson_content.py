import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LessonContent
from models import LearningProfile, User
from routers.auth import get_current_user
from schemas.lesson_content import (
    GenerateLessonContentRequest,
    LessonContentResponse,
)
from services.ai.normalization import normalize_language


router = APIRouter(
    prefix="/lesson-content",
    tags=["Lesson Content"],
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

LESSONS_DIR = (
    BASE_DIR
    / "data"
    / "lessons"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _language_fallbacks(language: str) -> list[str]:
    """
    Return the preferred instruction language followed by Arabic.

    Arabic is currently the canonical fallback because the lesson source
    content is being prepared with Arabic translations first.
    """
    language = normalize_language(language)

    if language == "ar":
        return ["ar"]

    return [language, "ar"]


def _load_canonical_lesson(lesson: CourseLesson) -> dict:
    """
    Load the canonical lesson JSON.

    Expected path:

        data/lessons/{language}/{level}/lesson_{order:02d}.json
    """

    language = normalize_language(lesson.language)
    level = str(lesson.level).upper()

    lesson_path = (
        LESSONS_DIR
        / language
        / level
        / f"lesson_{lesson.lesson_order:02d}.json"
    )

    if not lesson_path.exists():
        raise FileNotFoundError(
            f"Canonical lesson file not found: {lesson_path}"
        )

    try:
        with lesson_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid lesson JSON: {lesson_path}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Lesson JSON must contain an object: {lesson_path}"
        )

    return data


def _pick_translation(
    translations: dict | None,
    instruction_language: str,
) -> dict:
    """
    Select the requested translation.

    Fallback order:
        requested language -> Arabic -> empty object
    """

    if not isinstance(translations, dict):
        return {}

    for language in _language_fallbacks(instruction_language):
        value = translations.get(language)

        if isinstance(value, dict):
            return value

    return {}


def _materialize_section(
    section: dict,
    instruction_language: str,
) -> dict:
    """
    Convert one canonical section into a language-specific section.
    """

    content = section.get("content")

    if not isinstance(content, dict):
        content = {}

    translation = _pick_translation(
        section.get("translations"),
        instruction_language,
    )

    result = {
        "id": section.get("id"),
        "order": section.get("order"),
        "type": section.get("type"),
    }

    # Target-language content
    result["target_text"] = content.get(
        "target_text",
        "",
    )

    result["pronunciation"] = content.get(
        "pronunciation",
    )

    # Instruction-language content
    result["translation"] = translation.get(
        "translation",
        "",
    )

    result["explanation"] = translation.get(
        "explanation",
        "",
    )

    # Examples belong to the translation layer because their translations
    # depend on the instruction language.
    examples = translation.get("examples")

    if isinstance(examples, list):
        result["examples"] = examples

    return result


def _materialize_vocabulary_item(
    item: dict,
    instruction_language: str,
) -> dict:
    """
    Convert one canonical vocabulary item into the format expected
    by the existing Flutter model.
    """

    translation = _pick_translation(
        item.get("translations"),
        instruction_language,
    )

    return {
        "word": item.get("word", ""),
        "translation": translation.get(
            "translation",
            "",
        ),
        "part_of_speech": item.get(
            "part_of_speech",
        ),
        "pronunciation": item.get(
            "pronunciation",
        ),
    }


def _materialize_exercise(
    exercise: dict,
    instruction_language: str,
) -> dict:
    """
    Convert a canonical exercise into the existing Flutter format.
    """

    translation = _pick_translation(
        exercise.get("translations"),
        instruction_language,
    )

    return {
        "id": exercise.get("id"),
        "order": exercise.get("order"),
        "type": exercise.get(
            "type",
            "multiple_choice",
        ),
        "question": translation.get(
            "question",
            "",
        ),
        "options": translation.get(
            "options",
            [],
        ),
        "answer": exercise.get(
            "correct_answer",
            "",
        ),
        "explanation": translation.get(
            "explanation",
        ),
    }


def _materialize_review(
    review: dict,
    instruction_language: str,
) -> list[dict]:
    """
    Convert review items into the existing Flutter example structure.
    """

    items = review.get("items")

    if not isinstance(items, list):
        return []

    result = []

    for item in items:
        if not isinstance(item, dict):
            continue

        translation = _pick_translation(
            item.get("translations"),
            instruction_language,
        )

        result.append(
            {
                "target_text": item.get(
                    "target_text",
                    "",
                ),
                "translation": translation.get(
                    "translation",
                    "",
                ),
                "pronunciation": item.get(
                    "pronunciation",
                ),
            }
        )

    return result


def _materialize_end_test(
    end_test: dict,
    instruction_language: str,
) -> list[dict]:
    """
    Convert fixed end-test questions into the same exercise format
    used by the Flutter client.
    """

    questions = end_test.get("questions")

    if not isinstance(questions, list):
        return []

    result = []

    for question in questions:
        if not isinstance(question, dict):
            continue

        result.append(
            _materialize_exercise(
                question,
                instruction_language,
            )
        )

    return result


def _materialize_lesson(
    canonical: dict,
    instruction_language: str,
) -> dict:
    """
    Convert the canonical multilingual lesson JSON into the stable
    LessonContent API shape already used by Flutter.

    Important:
        - language = target language
        - instruction_language = explanation/translation language
        - target words are never translated into another target language
        - IDs remain stable
        - fixed tests remain fixed
    """

    instruction_language = normalize_language(
        instruction_language
    )

    metadata = canonical.get("metadata")

    if not isinstance(metadata, dict):
        metadata = {}

    metadata_translation = _pick_translation(
        metadata.get("translations"),
        instruction_language,
    )

    sections = canonical.get("sections")

    if not isinstance(sections, list):
        sections = []

    materialized_sections = [
        _materialize_section(
            section,
            instruction_language,
        )
        for section in sections
        if isinstance(section, dict)
    ]

    vocabulary = canonical.get("vocabulary")

    if not isinstance(vocabulary, list):
        vocabulary = []

    materialized_vocabulary = [
        _materialize_vocabulary_item(
            item,
            instruction_language,
        )
        for item in vocabulary
        if isinstance(item, dict)
    ]

    exercises = canonical.get("exercises")

    if not isinstance(exercises, list):
        exercises = []

    materialized_exercises = [
        _materialize_exercise(
            exercise,
            instruction_language,
        )
        for exercise in exercises
        if isinstance(exercise, dict)
    ]

    review = canonical.get("review")

    if not isinstance(review, dict):
        review = {}

    review_items = _materialize_review(
        review,
        instruction_language,
    )

    end_test = canonical.get("end_test")

    if not isinstance(end_test, dict):
        end_test = {}

    end_test_items = _materialize_end_test(
        end_test,
        instruction_language,
    )

    # Use the first sections as the existing Flutter lesson fields.
    introduction = ""
    explanation = ""
    examples = []
    dialogue = []

    for section in materialized_sections:
        section_type = section.get("type")

        if section_type == "explanation":
            if not explanation:
                explanation = section.get(
                    "explanation",
                    "",
                )

        if section_type == "micro_review":
            if not introduction:
                introduction = section.get(
                    "translation",
                    "",
                )

        section_examples = section.get("examples")

        if isinstance(section_examples, list):
            examples.extend(
                [
                    {
                        "target_text": item.get(
                            "target_text",
                            "",
                        ),
                        "translation": item.get(
                            "translation",
                            "",
                        ),
                    }
                    for item in section_examples
                    if isinstance(item, dict)
                ]
            )

    return {
        "title": metadata_translation.get(
            "title",
            canonical.get("lesson_id", ""),
        ),
        "objective": metadata_translation.get(
            "objective",
            "",
        ),
        "introduction": introduction,
        "explanation": explanation,
        "vocabulary": materialized_vocabulary,
        "examples": examples,
        "dialogue": dialogue,
        "exercises": materialized_exercises,

        # Extra canonical information.
        # Flutter can ignore these fields until we decide to expose them.
        "sections": materialized_sections,
        "review": review_items,
        "end_test": {
            "passing_score": end_test.get(
                "passing_score",
                80,
            ),
            "question_count": end_test.get(
                "question_count",
                len(end_test_items),
            ),
            "questions": end_test_items,
        },
    }


def _create_or_update_lesson_content(
    db: Session,
    lesson: CourseLesson,
    instruction_language: str,
) -> LessonContent:
    """
    Materialize canonical JSON into LessonContent.

    No Gemini/API call is made here.
    """

    instruction_language = normalize_language(
        instruction_language
    )

    canonical = _load_canonical_lesson(lesson)

    materialized_content = _materialize_lesson(
        canonical,
        instruction_language,
    )

    existing = (
        db.query(LessonContent)
        .filter(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language
            == instruction_language,
        )
        .first()
    )

    if existing is None:
        existing = LessonContent(
            lesson_id=lesson.id,
            instruction_language=instruction_language,
            status="READY",
            content=materialized_content,
            generator_model="canonical-json",
            generation_error=None,
            version=1,
        )

        db.add(existing)
    else:
        existing.status = "READY"
        existing.content = materialized_content
        existing.generator_model = "canonical-json"
        existing.generation_error = None
        existing.version = (existing.version or 0) + 1

    db.commit()
    db.refresh(existing)

    return existing


# ---------------------------------------------------------------------------
# GET lesson content
# ---------------------------------------------------------------------------

@router.get(
    "/{lesson_id}",
    response_model=LessonContentResponse,
)
def get_lesson_content(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = db.get(
        CourseLesson,
        lesson_id,
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    user_language = normalize_language(
        current_user.learning_language
    )

    if normalize_language(
        lesson.language
    ) != user_language:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This lesson does not belong "
                "to your learning language."
            ),
        )

    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == user_language,
        )
        .first()
    )

    if profile is None or profile.level != lesson.level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This lesson is not part of "
                "your current learning level."
            ),
        )

    instruction_language = normalize_language(
        current_user.native_language
    )

    content = (
        db.query(LessonContent)
        .filter(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language
            == instruction_language,
            LessonContent.status == "READY",
        )
        .first()
    )

    # If the requested language has not yet been materialized,
    # build it directly from the canonical JSON.
    if content is None:
        try:
            content = _create_or_update_lesson_content(
                db=db,
                lesson=lesson,
                instruction_language=instruction_language,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson content source file was not found.",
            )
        except ValueError as exc:
            logger.exception(
                "Invalid canonical lesson lesson_id=%s",
                lesson.id,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception(
                "Failed to materialize lesson lesson_id=%s: %s",
                lesson.id,
                exc,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare lesson content.",
            ) from exc

    return content


# ---------------------------------------------------------------------------
# Generate / materialize lesson content
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=LessonContentResponse,
)
def generate_lesson(
    request: GenerateLessonContentRequest,
    x_lesson_generator_token: str | None = Header(
        default=None
    ),
    db: Session = Depends(get_db),
):
    """
    Materialize a canonical lesson JSON into LessonContent.

    Despite the historical endpoint name /generate, this endpoint
    no longer calls Gemini.

    The canonical lesson JSON is the source of truth.
    """

    expected_token = os.getenv(
        "LESSON_GENERATOR_TOKEN"
    )

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lesson generator is not configured.",
        )

    if x_lesson_generator_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid lesson generator token.",
        )

    lesson = db.get(
        CourseLesson,
        request.lesson_id,
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    instruction_language = normalize_language(
        request.instruction_language
    )

    existing = (
        db.query(LessonContent)
        .filter(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language
            == instruction_language,
        )
        .first()
    )

    if (
        existing is not None
        and existing.status == "READY"
        and not request.force_regenerate
    ):
        return existing

    try:
        content = _create_or_update_lesson_content(
            db=db,
            lesson=lesson,
            instruction_language=instruction_language,
        )

        logger.info(
            "Lesson materialized from canonical JSON "
            "lesson_id=%s language=%s level=%s topic=%s "
            "instruction_language=%s",
            lesson.id,
            lesson.language,
            lesson.level,
            lesson.topic_key,
            instruction_language,
        )

        return content

    except FileNotFoundError as exc:
        logger.exception(
            "Canonical lesson source missing lesson_id=%s",
            lesson.id,
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canonical lesson content was not found.",
        ) from exc

    except ValueError as exc:
        logger.exception(
            "Invalid canonical lesson lesson_id=%s",
            lesson.id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Lesson materialization failed lesson_id=%s: %s",
            lesson.id,
            exc,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson content preparation failed.",
        ) from exc