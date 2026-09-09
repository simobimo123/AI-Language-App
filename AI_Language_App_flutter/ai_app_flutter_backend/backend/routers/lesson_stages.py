from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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

STAGES = ("teaching", "practice")
STATUS_LOCKED = "locked"
STATUS_AVAILABLE = "available"
STATUS_COMPLETED = "completed"


class CompleteStageRequest(BaseModel):
    stage: str = Field(min_length=1, max_length=20)
    conversation_id: str | None = Field(default=None, max_length=120)


def _get_learning_profile(db: Session, user: User, lesson: CourseLesson) -> LearningProfile:
    profile = db.scalar(
        select(LearningProfile).where(
            LearningProfile.user_id == user.id,
            LearningProfile.language == lesson.language,
        )
    )
    if profile is None:
        raise HTTPException(status_code=400, detail="Learning profile not found for this lesson language.")
    return profile


def _get_or_create_stage_progress(
    db: Session,
    user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
) -> UserLessonStageProgress:
    progress = db.scalar(
        select(UserLessonStageProgress).where(
            UserLessonStageProgress.user_id == user.id,
            UserLessonStageProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        progress = UserLessonStageProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            teaching_status=STATUS_AVAILABLE,
            practice_status=STATUS_LOCKED,
        )
        db.add(progress)
        db.flush()
    else:
        if progress.teaching_status == STATUS_LOCKED:
            progress.teaching_status = STATUS_AVAILABLE
        if progress.teaching_status == STATUS_COMPLETED and progress.practice_status == STATUS_LOCKED:
            progress.practice_status = STATUS_AVAILABLE
    return progress


def _sync_unlocked_statuses(progress: UserLessonStageProgress) -> None:
    if progress.teaching_status == STATUS_COMPLETED and progress.practice_status == STATUS_LOCKED:
        progress.practice_status = STATUS_AVAILABLE


def _serialize(progress: UserLessonStageProgress) -> dict:
    _sync_unlocked_statuses(progress)
    return {
        "lesson_id": progress.lesson_id,
        "stages": {
            "teaching": progress.teaching_status,
            "practice": progress.practice_status,
        },
        "conversations": {
            "teaching": progress.teaching_conversation_id,
            "practice": progress.practice_conversation_id,
        },
        "timestamps": {
            "teaching_started_at": progress.teaching_started_at,
            "teaching_completed_at": progress.teaching_completed_at,
            "practice_started_at": progress.practice_started_at,
            "practice_completed_at": progress.practice_completed_at,
        },
        "lesson_completed": progress.practice_status == STATUS_COMPLETED,
    }


def _get_lesson(db: Session, lesson_id: int) -> CourseLesson:
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return lesson


@router.get("/{lesson_id}/stages")
def get_lesson_stages(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lesson = _get_lesson(db, lesson_id)
    profile = _get_learning_profile(db, current_user, lesson)
    progress = _get_or_create_stage_progress(db, current_user, profile, lesson)
    _sync_unlocked_statuses(progress)
    db.commit()
    return _serialize(progress)


@router.post("/{lesson_id}/stages/complete")
def complete_lesson_stage(
    lesson_id: int,
    payload: CompleteStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stage = payload.stage.strip().lower()
    if stage not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid lesson stage.")

    lesson = _get_lesson(db, lesson_id)
    profile = _get_learning_profile(db, current_user, lesson)
    progress = _get_or_create_stage_progress(db, current_user, profile, lesson)
    _sync_unlocked_statuses(progress)

    current_status = getattr(progress, f"{stage}_status")
    if current_status == STATUS_COMPLETED:
        return _serialize(progress)
    if current_status == STATUS_LOCKED:
        raise HTTPException(status_code=409, detail=f"Stage '{stage}' is locked until the previous stage is completed.")

    now = datetime.utcnow()

    if stage == "teaching":
        if progress.teaching_started_at is None:
            progress.teaching_started_at = now
        progress.teaching_status = STATUS_COMPLETED
        progress.teaching_completed_at = now
        if payload.conversation_id:
            progress.teaching_conversation_id = payload.conversation_id
        _sync_unlocked_statuses(progress)

    else:
        if progress.teaching_status != STATUS_COMPLETED:
            raise HTTPException(status_code=409, detail="Practice cannot be completed before AI teaching.")
        if progress.practice_started_at is None:
            progress.practice_started_at = now
        progress.practice_status = STATUS_COMPLETED
        progress.practice_completed_at = now
        if payload.conversation_id:
            progress.practice_conversation_id = payload.conversation_id

        lesson_progress = db.scalar(
            select(UserLessonProgress).where(
                UserLessonProgress.user_id == current_user.id,
                UserLessonProgress.lesson_id == lesson.id,
            )
        )
        if lesson_progress is None:
            lesson_progress = UserLessonProgress(
                user_id=current_user.id,
                learning_profile_id=profile.id,
                lesson_id=lesson.id,
            )
            db.add(lesson_progress)
        lesson_progress.completed = True
        lesson_progress.completed_at = now

    db.commit()
    db.refresh(progress)
    return _serialize(progress)
