from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LessonPracticeScenario,
    LessonTarget,
    LessonTargetPattern,
    User,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/lessons", tags=["Lesson Curriculum"])


@router.get("/{lesson_id}/curriculum")
def get_lesson_curriculum(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the normalized curriculum used by AI teaching and practice."""
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found.")

    targets = db.scalars(
        select(LessonTarget)
        .where(LessonTarget.lesson_id == lesson_id)
        .order_by(LessonTarget.target_order)
    ).all()

    target_payload = []
    for target in targets:
        patterns = db.scalars(
            select(LessonTargetPattern)
            .where(LessonTargetPattern.target_id == target.id)
            .order_by(LessonTargetPattern.id)
        ).all()
        target_payload.append(
            {
                "id": target.target_key,
                "order": target.target_order,
                "goal": target.goal,
                "required": target.required,
                "cefr_level": target.cefr_level,
                "patterns": [pattern.pattern for pattern in patterns],
            }
        )

    scenarios = db.scalars(
        select(LessonPracticeScenario)
        .where(LessonPracticeScenario.lesson_id == lesson_id)
        .order_by(LessonPracticeScenario.scenario_order)
    ).all()

    return {
        "lesson_id": lesson.id,
        "language": lesson.language,
        "level": lesson.level,
        "topic_key": lesson.topic_key,
        "targets": target_payload,
        "practice_scenarios": [
            {
                "id": scenario.scenario_key,
                "order": scenario.scenario_order,
                "title": scenario.title,
                "context": scenario.context,
                "instructions": scenario.instructions,
                "target_ids": [
                    target.target_key
                    for target in targets
                    if target.id in (scenario.target_ids or [])
                ],
            }
            for scenario in scenarios
        ],
    }
