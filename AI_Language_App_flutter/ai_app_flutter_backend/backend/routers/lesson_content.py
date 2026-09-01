import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LessonContent, LearningProfile, User
from routers.auth import get_current_user
from schemas.lesson_content import (
    GenerateLessonContentRequest,
    LessonContentResponse,
)
from services.ai.client import AI_MODEL
from services.ai.lesson_generator import generate_lesson_content
from services.ai.normalization import normalize_language


router = APIRouter(
    prefix="/lesson-content",
    tags=["Lesson Content"],
)

logger = logging.getLogger(__name__)


@router.get(
    "/{lesson_id}",
    response_model=LessonContentResponse,
)
def get_lesson_content(
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

    content = (
        db.query(LessonContent)
        .filter(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language == normalize_language(
                current_user.native_language
            ),
            LessonContent.status == "READY",
        )
        .first()
    )

    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson content is not available yet.",
        )

    return content


@router.post(
    "/generate",
    response_model=LessonContentResponse,
)
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
            LessonContent.instruction_language == instruction_language,
        )
        .first()
    )

    if existing is not None and existing.status == "READY" and not request.force_regenerate:
        return existing

    if existing is None:
        existing = LessonContent(
            lesson_id=lesson.id,
            instruction_language=instruction_language,
            status="GENERATING",
            content={},
            generator_model=AI_MODEL,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
    else:
        existing.status = "GENERATING"
        existing.generation_error = None
        existing.generator_model = AI_MODEL
        db.commit()

    try:
        generated, prompt_tokens, completion_tokens, total_tokens = (
            generate_lesson_content(
                lesson=lesson,
                instruction_language=instruction_language,
            )
        )

        existing.content = generated.model_dump()
        existing.status = "READY"
        existing.generator_model = AI_MODEL
        existing.generation_error = None
        existing.version = (existing.version or 0) + 1

        db.commit()
        db.refresh(existing)

        logger.info(
            "Lesson generated lesson_id=%s language=%s level=%s topic=%s "
            "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            lesson.id,
            lesson.language,
            lesson.level,
            lesson.topic_key,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

        return existing

    except Exception as exc:
        logger.exception(
            "Lesson generation failed lesson_id=%s: %s",
            lesson.id,
            exc,
        )

        db.rollback()

        existing = db.get(LessonContent, existing.id)
        if existing is not None:
            existing.status = "FAILED"
            existing.generation_error = str(exc)[:4000]
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Lesson generation failed.",
        ) from exc
