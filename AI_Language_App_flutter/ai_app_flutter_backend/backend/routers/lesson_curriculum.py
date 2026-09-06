from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LessonLearningItem,
    LessonLearningQuestion,
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
    """Return the normalized curriculum needed by the three lesson stages."""
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

    items = db.scalars(
        select(LessonLearningItem)
        .where(LessonLearningItem.lesson_id == lesson_id)
        .order_by(LessonLearningItem.item_order)
    ).all()

    questions = db.scalars(
        select(LessonLearningQuestion)
        .where(LessonLearningQuestion.lesson_id == lesson_id)
        .order_by(LessonLearningQuestion.question_order)
    ).all()

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
        "learning_items": [
            {
                "id": item.item_key,
                "order": item.item_order,
                "type": item.item_type,
                "target_id": next(
                    (
                        target.target_key
                        for target in targets
                        if target.id == item.target_id
                    ),
                    None,
                ),
                "target_text": item.target_text,
                "pronunciation": item.pronunciation,
                "translations": item.translations,
                "extra_data": item.extra_data,
            }
            for item in items
        ],
        "questions": [
            {
                "id": question.question_key,
                "order": question.question_order,
                "type": question.question_type,
                "target_id": next(
                    (
                        target.target_key
                        for target in targets
                        if target.id == question.target_id
                    ),
                    None,
                ),
                "correct_answer": question.correct_answer,
                "accepted_answers": question.accepted_answers,
                "translations": question.translations,
            }
            for question in questions
        ],
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
