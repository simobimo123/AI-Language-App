from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LearningProfile,
    User,
    UserLessonProgress,
    UserLessonStageProgress,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/lessons", tags=["Lesson Stages"])

VALID_STAGES = {"learn", "teaching", "practice"}


class CompleteStageRequest(BaseModel):
    stage: str = Field(min_length=1, max_length=20)
    conversation_id: str | None = Field(default=None, max_length=120)


def _get_profile_and_lesson(
    lesson_id: int,
    current_user: User,
    db: Session,
) -> tuple[LearningProfile, CourseLesson]:
    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id == current_user.id
        )
    ).scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning profile not found.",
        )

    lesson = db.execute(
        select(CourseLesson).where(CourseLesson.id == lesson_id)
    ).scalar_one_or_none()

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found.",
        )

    return profile, lesson


def _get_or_create_stage_progress(
    current_user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    db: Session,
) -> UserLessonStageProgress:
    row = db.execute(
        select(UserLessonStageProgress).where(
            UserLessonStageProgress.user_id == current_user.id,
            UserLessonStageProgress.lesson_id == lesson.id,
        )
    ).scalar_one_or_none()

    if row is None:
        row = UserLessonStageProgress(
            user_id=current_user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
        )
        db.add(row)
        db.flush()

    return row


def _response(row: UserLessonStageProgress) -> dict:
    completed = (
        row.practice_status == "completed"
    )
    return {
        "lesson_id": row.lesson_id,
        "completed": completed,
        "stages": {
            "learn": {"status": row.learn_status},
            "teaching": {
                "status": row.teaching_status,
                "conversation_id": row.teaching_conversation_id,
            },
            "practice": {
                "status": row.practice_status,
                "conversation_id": row.practice_conversation_id,
            },
        },
    }


@router.get("/{lesson_id}/stages")
def get_lesson_stages(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile, lesson = _get_profile_and_lesson(lesson_id, current_user, db)
    row = _get_or_create_stage_progress(current_user, profile, lesson, db)
    db.commit()
    return _response(row)


@router.post("/{lesson_id}/stages/complete")
def complete_lesson_stage(
    lesson_id: int,
    request: CompleteStageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stage = request.stage.strip().lower()
    if stage not in VALID_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson stage.",
        )

    profile, lesson = _get_profile_and_lesson(lesson_id, current_user, db)
    row = _get_or_create_stage_progress(current_user, profile, lesson, db)

    if stage == "learn":
        if row.learn_status != "completed":
            row.learn_status = "completed"
        if row.teaching_status == "locked":
            row.teaching_status = "available"

    elif stage == "teaching":
        if row.learn_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete the interactive learning stage first.",
            )
        row.teaching_status = "completed"
        if request.conversation_id:
            row.teaching_conversation_id = request.conversation_id
        if row.practice_status == "locked":
            row.practice_status = "available"

    elif stage == "practice":
        if row.learn_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete the interactive learning stage first.",
            )
        if row.teaching_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Complete the AI teaching stage first.",
            )
        row.practice_status = "completed"
        if request.conversation_id:
            row.practice_conversation_id = request.conversation_id

        lesson_progress = db.execute(
            select(UserLessonProgress).where(
                UserLessonProgress.user_id == current_user.id,
                UserLessonProgress.lesson_id == lesson.id,
            )
        ).scalar_one_or_none()

        if lesson_progress is None:
            lesson_progress = UserLessonProgress(
                user_id=current_user.id,
                learning_profile_id=profile.id,
                lesson_id=lesson.id,
            )
            db.add(lesson_progress)

        lesson_progress.completed = True
        lesson_progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(row)
    return _response(row)
