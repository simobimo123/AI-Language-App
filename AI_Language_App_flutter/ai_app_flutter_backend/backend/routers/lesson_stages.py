from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LearningProfile,
    LessonTarget,
    User,
    UserLessonProgress,
    UserLessonStageProgress,
    UserLessonTargetProgress,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/lessons", tags=["Lesson Stages"])

STAGES = ("learn", "teaching", "practice")
STATUS_LOCKED = "locked"
STATUS_AVAILABLE = "available"
STATUS_COMPLETED = "completed"


class CompleteStageRequest(BaseModel):
    stage: str = Field(min_length=1, max_length=20)
    conversation_id: str | None = Field(default=None, max_length=120)


def _get_learning_profile(db: Session, user: User, lesson: CourseLesson) -> LearningProfile:
    profile = db.scalar(select(LearningProfile).where(
        LearningProfile.user_id == user.id,
        LearningProfile.language == lesson.language,
    ))
    if profile is None:
        raise HTTPException(status_code=400, detail="Learning profile not found for this lesson language.")
    return profile


def _get_or_create_stage_progress(db: Session, user: User, profile: LearningProfile, lesson: CourseLesson) -> UserLessonStageProgress:
    progress = db.scalar(select(UserLessonStageProgress).where(
        UserLessonStageProgress.user_id == user.id,
        UserLessonStageProgress.lesson_id == lesson.id,
    ))
    if progress is None:
        progress = UserLessonStageProgress(
            user_id=user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            learn_status=STATUS_AVAILABLE,
            teaching_status=STATUS_LOCKED,
            practice_status=STATUS_LOCKED,
        )
        db.add(progress)
        db.flush()
    return progress


def _sync_unlocked_statuses(progress: UserLessonStageProgress) -> None:
    if progress.learn_status == STATUS_COMPLETED and progress.teaching_status == STATUS_LOCKED:
        progress.teaching_status = STATUS_AVAILABLE
    if progress.teaching_status == STATUS_COMPLETED and progress.practice_status == STATUS_LOCKED:
        progress.practice_status = STATUS_AVAILABLE


def _serialize(progress: UserLessonStageProgress) -> dict:
    _sync_unlocked_statuses(progress)
    return {
        "lesson_id": progress.lesson_id,
        "stages": {
            "learn": progress.learn_status,
            "teaching": progress.teaching_status,
            "practice": progress.practice_status,
        },
        "conversations": {
            "teaching": progress.teaching_conversation_id,
            "practice": progress.practice_conversation_id,
        },
        "timestamps": {
            "learn_started_at": progress.learn_started_at,
            "learn_completed_at": progress.learn_completed_at,
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


def _required_targets_completed(db: Session, user_id: int, lesson_id: int, stage: str) -> bool:
    targets = db.scalars(select(LessonTarget).where(
        LessonTarget.lesson_id == lesson_id,
        LessonTarget.required.is_(True),
    )).all()
    if not targets:
        return False

    target_ids = [target.id for target in targets]
    rows = db.scalars(select(UserLessonTargetProgress).where(
        UserLessonTargetProgress.user_id == user_id,
        UserLessonTargetProgress.lesson_id == lesson_id,
        UserLessonTargetProgress.target_id.in_(target_ids),
    )).all()
    by_target = {row.target_id: row for row in rows}

    field = "teaching_status" if stage == "teaching" else "practice_status"
    return all(getattr(by_target.get(target.id), field, None) == STATUS_COMPLETED for target in targets)


@router.get("/{lesson_id}/stages")
def get_lesson_stages(lesson_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lesson = _get_lesson(db, lesson_id)
    profile = _get_learning_profile(db, current_user, lesson)
    progress = _get_or_create_stage_progress(db, current_user, profile, lesson)
    _sync_unlocked_statuses(progress)
    db.commit()
    return _serialize(progress)


@router.post("/{lesson_id}/stages/complete")
def complete_lesson_stage(lesson_id: int, payload: CompleteStageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

    if stage == "learn":
        if progress.learn_started_at is None:
            progress.learn_started_at = now
        progress.learn_status = STATUS_COMPLETED
        progress.learn_completed_at = now
        _sync_unlocked_statuses(progress)

    elif stage == "teaching":
        if progress.learn_status != STATUS_COMPLETED:
            raise HTTPException(status_code=409, detail="Teaching cannot be completed before interactive learning.")
        if not _required_targets_completed(db, current_user.id, lesson.id, "teaching"):
            raise HTTPException(status_code=409, detail="Teaching cannot be completed until all required targets are mastered.")
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
        if not _required_targets_completed(db, current_user.id, lesson.id, "practice"):
            raise HTTPException(status_code=409, detail="Practice cannot be completed until all required targets are demonstrated.")
        if progress.practice_started_at is None:
            progress.practice_started_at = now
        progress.practice_status = STATUS_COMPLETED
        progress.practice_completed_at = now
        if payload.conversation_id:
            progress.practice_conversation_id = payload.conversation_id

        lesson_progress = db.scalar(select(UserLessonProgress).where(
            UserLessonProgress.user_id == current_user.id,
            UserLessonProgress.lesson_id == lesson.id,
        ))
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
