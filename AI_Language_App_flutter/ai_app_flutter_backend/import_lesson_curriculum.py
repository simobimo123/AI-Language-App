"""Import canonical lesson JSON into normalized curriculum tables.

The JSON files remain the authoring/source format. This module mirrors their
three-stage curriculum data into PostgreSQL so runtime services can use stable
foreign keys and persistent learner progress.

The sync is intentionally reusable by the API startup lifecycle as well as the
standalone CLI entry point. It is idempotent: unchanged lesson files do not
cause unnecessary database writes or version bumps.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    CourseLesson,
    LessonContent,
    LessonLearningItem,
    LessonLearningQuestion,
    LessonPracticeScenario,
    LessonTarget,
    LessonTargetPattern,
)


BASE_DIR = Path(__file__).resolve().parent
# This importer lives in ai_app_flutter_backend/, while the canonical lesson
# files live in ai_app_flutter_backend/backend/data/lessons/.
LESSONS_DIR = BASE_DIR / "backend" / "data" / "lessons"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Lesson JSON must contain an object: {path}")
    return data


def _course_lesson(db: Session, data: dict) -> CourseLesson | None:
    return db.scalar(
        select(CourseLesson).where(
            CourseLesson.language == str(data.get("language", "")).lower(),
            CourseLesson.level == str(data.get("level", "")).upper(),
            CourseLesson.lesson_order == int(data["lesson_order"]),
        )
    )


def _upsert_content(db: Session, lesson: CourseLesson, data: dict) -> None:
    canonical = data.get("lesson")
    if not isinstance(canonical, dict):
        canonical = {}

    existing = db.scalar(
        select(LessonContent).where(
            LessonContent.lesson_id == lesson.id,
            LessonContent.instruction_language == "ar",
        )
    )

    if existing is None:
        db.add(
            LessonContent(
                lesson_id=lesson.id,
                instruction_language="ar",
                status="PUBLISHED",
                content=data,
                version=1,
            )
        )
        return

    if existing.content == data and existing.status == "PUBLISHED":
        return

    existing.content = data
    existing.status = "PUBLISHED"
    existing.version += 1


def _upsert_target(db: Session, lesson: CourseLesson, target_data: dict) -> LessonTarget:
    key = str(target_data.get("id", "")).strip()
    if not key:
        raise ValueError(f"Target without id in lesson {lesson.id}")

    target = db.scalar(
        select(LessonTarget).where(
            LessonTarget.lesson_id == lesson.id,
            LessonTarget.target_key == key,
        )
    )

    if target is None:
        target = LessonTarget(
            lesson_id=lesson.id,
            target_key=key,
            target_order=int(target_data.get("order", 1)),
            goal=str(target_data.get("goal", "")).strip(),
            required=bool(target_data.get("required", True)),
            cefr_level=lesson.level,
        )
        db.add(target)
    else:
        target.target_order = int(target_data.get("order", target.target_order))
        target.goal = str(target_data.get("goal", target.goal)).strip()
        target.required = bool(target_data.get("required", target.required))
        target.cefr_level = lesson.level

    db.flush()
    return target


def _upsert_patterns(db: Session, target: LessonTarget, target_data: dict) -> None:
    patterns = target_data.get("patterns", [])
    if not isinstance(patterns, list):
        patterns = []

    for pattern in patterns:
        value = str(pattern).strip()
        if not value:
            continue

        row = db.scalar(
            select(LessonTargetPattern).where(
                LessonTargetPattern.target_id == target.id,
                LessonTargetPattern.pattern == value,
            )
        )
        if row is None:
            db.add(
                LessonTargetPattern(
                    target_id=target.id,
                    pattern=value,
                    pattern_type="expected",
                )
            )

    suggestion = str(target_data.get("suggestion", "")).strip()
    if suggestion and suggestion not in patterns:
        row = db.scalar(
            select(LessonTargetPattern).where(
                LessonTargetPattern.target_id == target.id,
                LessonTargetPattern.pattern == suggestion,
            )
        )
        if row is None:
            db.add(
                LessonTargetPattern(
                    target_id=target.id,
                    pattern=suggestion,
                    pattern_type="suggestion",
                )
            )


def _upsert_learning_items(db: Session, lesson: CourseLesson, sections: list, targets_by_order: dict[int, LessonTarget]) -> None:
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue

        item_key = str(section.get("id", f"section_{index}")).strip()
        content = section.get("content")
        if not isinstance(content, dict):
            content = {}

        target = targets_by_order.get(int(section.get("order", index)))
        translations = section.get("translations")
        if not isinstance(translations, dict):
            translations = {}

        row = db.scalar(
            select(LessonLearningItem).where(
                LessonLearningItem.lesson_id == lesson.id,
                LessonLearningItem.item_key == item_key,
            )
        )

        values = {
            "lesson_id": lesson.id,
            "target_id": target.id if target else None,
            "item_key": item_key,
            "item_order": int(section.get("order", index)),
            "item_type": str(section.get("type", "teaching")),
            "target_text": str(content.get("target_text", "")).strip(),
            "pronunciation": content.get("pronunciation"),
            "translations": translations,
            "extra_data": {
                key: value
                for key, value in section.items()
                if key not in {"id", "order", "type", "content", "translations"}
            },
        }

        if row is None:
            db.add(LessonLearningItem(**values))
        else:
            for key, value in values.items():
                setattr(row, key, value)


def _upsert_questions(db: Session, lesson: CourseLesson, exercises: list, targets_by_order: dict[int, LessonTarget]) -> None:
    for index, exercise in enumerate(exercises, start=1):
        if not isinstance(exercise, dict):
            continue

        key = str(exercise.get("id", f"question_{index}")).strip()
        translations = exercise.get("translations")
        if not isinstance(translations, dict):
            translations = {}

        accepted = exercise.get("accepted_answers", [])
        if not isinstance(accepted, list):
            accepted = []

        order = int(exercise.get("order", index))
        target = targets_by_order.get(order)

        row = db.scalar(
            select(LessonLearningQuestion).where(
                LessonLearningQuestion.lesson_id == lesson.id,
                LessonLearningQuestion.question_key == key,
            )
        )

        values = {
            "lesson_id": lesson.id,
            "target_id": target.id if target else None,
            "question_key": key,
            "question_order": order,
            "question_type": str(exercise.get("type", "multiple_choice")),
            "correct_answer": str(exercise.get("correct_answer", "")).strip(),
            "accepted_answers": accepted,
            "translations": translations,
        }

        if row is None:
            db.add(LessonLearningQuestion(**values))
        else:
            for field, value in values.items():
                setattr(row, field, value)


def _upsert_scenarios(db: Session, lesson: CourseLesson, canonical: dict, targets_by_key: dict[str, LessonTarget]) -> None:
    scenarios = canonical.get("practice_scenarios")
    if not isinstance(scenarios, list):
        scenarios = canonical.get("scenarios")
    if not isinstance(scenarios, list):
        scenarios = []

    if not scenarios:
        scenarios = [
            {
                "id": "default",
                "order": 1,
                "title": str(canonical.get("title", "Lesson practice")),
                "context": str(canonical.get("objective", "Practice the lesson targets in a natural conversation.")),
                "instructions": "Use the lesson targets naturally in conversation.",
                "target_ids": list(targets_by_key.keys()),
            }
        ]

    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            continue

        key = str(scenario.get("id") or scenario.get("scenario_key") or f"scenario_{index}").strip()
        raw_target_ids = scenario.get("target_ids", [])
        if not isinstance(raw_target_ids, list):
            raw_target_ids = []

        target_ids = []
        for target_key in raw_target_ids:
            target = targets_by_key.get(str(target_key))
            if target is not None:
                target_ids.append(target.id)

        row = db.scalar(
            select(LessonPracticeScenario).where(
                LessonPracticeScenario.lesson_id == lesson.id,
                LessonPracticeScenario.scenario_key == key,
            )
        )

        values = {
            "lesson_id": lesson.id,
            "scenario_key": key,
            "scenario_order": int(scenario.get("order", index)),
            "title": str(scenario.get("title", key)).strip(),
            "context": str(scenario.get("context", "")).strip(),
            "instructions": scenario.get("instructions"),
            "target_ids": target_ids,
        }

        if row is None:
            db.add(LessonPracticeScenario(**values))
        else:
            for field, value in values.items():
                setattr(row, field, value)


def import_lesson(db: Session, path: Path) -> bool:
    data = _load_json(path)
    lesson = _course_lesson(db, data)
    if lesson is None:
        print(f"SKIP {path}: CourseLesson not found")
        return False

    canonical = data.get("lesson")
    if not isinstance(canonical, dict):
        canonical = {}

    _upsert_content(db, lesson, data)

    raw_targets = canonical.get("targets", [])
    if not isinstance(raw_targets, list):
        raw_targets = []

    targets_by_key: dict[str, LessonTarget] = {}
    targets_by_order: dict[int, LessonTarget] = {}

    for target_data in raw_targets:
        if not isinstance(target_data, dict):
            continue
        target = _upsert_target(db, lesson, target_data)
        _upsert_patterns(db, target, target_data)
        targets_by_key[target.target_key] = target
        targets_by_order[target.target_order] = target

    sections = data.get("sections", [])
    if isinstance(sections, list):
        _upsert_learning_items(db, lesson, sections, targets_by_order)

    exercises = data.get("exercises", [])
    if isinstance(exercises, list):
        _upsert_questions(db, lesson, exercises, targets_by_order)

    _upsert_scenarios(db, lesson, canonical, targets_by_key)
    return True


def sync_lesson_curriculum(db: Session) -> int:
    """Synchronize every canonical lesson JSON into PostgreSQL."""
    imported = 0
    paths = sorted(LESSONS_DIR.glob("*/*/lesson_*.json"))

    for path in paths:
        if import_lesson(db, path):
            imported += 1

    return imported


def main() -> None:
    db = SessionLocal()
    try:
        imported = sync_lesson_curriculum(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Imported {imported} lesson curriculum file(s).")


if __name__ == "__main__":
    main()
