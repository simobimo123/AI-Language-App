import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LessonContent, LearningProfile, User
from routers.auth import get_current_user
from schemas.lesson_content import GenerateLessonContentRequest, LessonContentResponse
from services.ai.normalization import normalize_language

router = APIRouter(prefix="/lesson-content", tags=["Lesson Content"])
logger = logging.getLogger(__name__)
LESSONS_DIR = Path(__file__).resolve().parent.parent / "data" / "lessons"


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid lesson JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Lesson JSON must contain an object: {path}")
    return data


def _load_canonical_lesson(lesson: CourseLesson) -> dict:
    language = normalize_language(lesson.language)
    level = str(lesson.level).upper()
    lesson_dir = LESSONS_DIR / language / level / f"lesson_{lesson.lesson_order:02d}"
    legacy_path = LESSONS_DIR / language / level / f"lesson_{lesson.lesson_order:02d}.json"

    if legacy_path.exists():
        return _load_json(legacy_path)

    teaching_path = lesson_dir / "teaching.json"
    practice_path = lesson_dir / "practice.json"
    if not teaching_path.exists() or not practice_path.exists():
        raise FileNotFoundError(f"Lesson source files not found: {lesson_dir}")

    teaching = _load_json(teaching_path)
    practice = _load_json(practice_path)

    teaching_language = normalize_language(str(teaching.get("language", language)))
    practice_language = normalize_language(str(practice.get("language", language)))
    teaching_level = str(teaching.get("level", level)).upper()
    practice_level = str(practice.get("level", level)).upper()
    if teaching_language != practice_language or teaching_language != language:
        raise ValueError(f"Teaching/practice language mismatch: {lesson_dir}")
    if teaching_level != practice_level or teaching_level != level:
        raise ValueError(f"Teaching/practice level mismatch: {lesson_dir}")

    return {
        "format": "split_v1",
        "lesson_id": f"{language}_{level.lower()}_lesson_{lesson.lesson_order:02d}",
        "language": language,
        "level": level,
        "lesson_order": lesson.lesson_order,
        "teaching": teaching,
        "practice": practice,
    }


def _materialize_lesson(canonical: dict) -> dict:
    if canonical.get("format") == "split_v1":
        teaching = canonical.get("teaching")
        practice = canonical.get("practice")
        if not isinstance(teaching, dict) or not isinstance(practice, dict):
            raise ValueError("Split lesson must contain teaching and practice objects.")
        return {
            "format": "split_v1",
            "lesson_id": canonical.get("lesson_id", ""),
            "language": canonical.get("language", ""),
            "level": canonical.get("level", ""),
            "lesson_order": canonical.get("lesson_order"),
            "teaching": teaching,
            "practice": practice,
            "targets": teaching.get("targets", []),
            "sections": [],
            "exercises": [],
            "review": [],
            "end_test": {},
        }

    return canonical


def _create_or_update_lesson_content(
    db: Session,
    lesson: CourseLesson,
    instruction_language: str,
) -> LessonContent:
    del instruction_language  # Split lesson JSON is language-neutral runtime data.
    canonical = _load_canonical_lesson(lesson)
    materialized_content = _materialize_lesson(canonical)

    existing = (
        db.query(LessonContent)
        .filter(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language == "ar",
        )
        .first()
    )

    if existing is None:
        existing = LessonContent(
            lesson_id=lesson.id,
            instruction_language="ar",
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


@router.get("/{lesson_id}", response_model=LessonContentResponse)
def get_lesson_content(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    user_language = normalize_language(current_user.learning_language)
    if normalize_language(lesson.language) != user_language:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson does not belong to your learning language.",
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
            detail="This lesson is not part of your current learning level.",
        )

    try:
        content = _create_or_update_lesson_content(
            db=db,
            lesson=lesson,
            instruction_language=normalize_language(current_user.native_language),
        )
        return content
    except FileNotFoundError as exc:
        logger.exception("Lesson source missing lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson content source was not found.") from exc
    except ValueError as exc:
        logger.exception("Invalid lesson source lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to materialize lesson lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to prepare lesson content.") from exc


@router.post("/generate", response_model=LessonContentResponse)
def generate_lesson(
    request: GenerateLessonContentRequest,
    x_lesson_generator_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    expected_token = os.getenv("LESSON_GENERATOR_TOKEN")
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

    lesson = db.get(CourseLesson, request.lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    try:
        return _create_or_update_lesson_content(
            db=db,
            lesson=lesson,
            instruction_language=normalize_language(request.instruction_language),
        )
    except FileNotFoundError as exc:
        logger.exception("Lesson source missing lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canonical lesson content was not found.") from exc
    except ValueError as exc:
        logger.exception("Invalid lesson source lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Lesson materialization failed lesson_id=%s", lesson.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lesson content preparation failed.") from exc
