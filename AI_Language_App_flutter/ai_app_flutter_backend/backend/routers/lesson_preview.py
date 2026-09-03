import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LearningProfile, User
from routers.auth import get_current_user
from services.ai.normalization import normalize_language


router = APIRouter(
    prefix="/lesson-preview",
    tags=["Lesson Preview"],
)


LESSONS_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "lessons"
)


def _load_lesson_json(lesson: CourseLesson) -> dict:
    language = normalize_language(lesson.language)
    level = str(lesson.level).upper()
    path = (
        LESSONS_DIR
        / language
        / level
        / f"lesson_{lesson.lesson_order:02d}.json"
    )

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson preview source file was not found.",
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson preview source is invalid.",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson preview source is invalid.",
        )

    return data


def _list_of_strings(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@router.get("/{lesson_id}")
def get_lesson_preview(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson = db.get(CourseLesson, lesson_id)

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    learning_language = normalize_language(
        current_user.learning_language
    )

    if normalize_language(lesson.language) != learning_language:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson does not belong to your learning language.",
        )

    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == learning_language,
        )
        .first()
    )

    if profile is None or profile.level != lesson.level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is not part of your current learning level.",
        )

    data = _load_lesson_json(lesson)

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    preview = data.get("preview")
    if not isinstance(preview, dict):
        preview = {}

    # Intentionally exclude new_vocabulary/new_items. Those are shown after
    # successful completion, not before starting the lesson.
    what_you_will_learn = _list_of_strings(
        preview.get("what_you_will_learn")
    )
    skills = _list_of_strings(metadata.get("skills"))

    return {
        "lesson_id": data.get("lesson_id", ""),
        "language": data.get("language", lesson.language),
        "level": data.get("level", lesson.level),
        "lesson_order": data.get("lesson_order", lesson.lesson_order),
        "title": metadata.get("title") or lesson.topic_key,
        "objective": metadata.get("objective") or "",
        "description": metadata.get("description") or "",
        "estimated_minutes": metadata.get("estimated_minutes"),
        "what_you_will_learn": what_you_will_learn,
        "skills": skills,
    }
