"""Import canonical lesson curriculum from split teaching/practice JSON files."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    CourseLesson,
    LessonContent,
    LessonPracticeScenario,
    LessonTarget,
    LessonTargetPattern,
)

BASE_DIR = Path(__file__).resolve().parent
LESSONS_DIR = BASE_DIR / "backend" / "data" / "lessons"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Lesson JSON must contain an object: {path}")
    return data


def _load_split_lesson(folder: Path) -> tuple[dict, dict]:
    teaching_path = folder / "teaching.json"
    practice_path = folder / "practice.json"

    if not teaching_path.exists():
        raise FileNotFoundError(f"Missing teaching.json: {teaching_path}")
    if not practice_path.exists():
        raise FileNotFoundError(f"Missing practice.json: {practice_path}")

    teaching = _load_json(teaching_path)
    practice = _load_json(practice_path)

    language = str(teaching.get("language", "")).lower().strip()
    practice_language = str(practice.get("language", "")).lower().strip()
    level = str(teaching.get("level", "")).upper().strip()
    practice_level = str(practice.get("level", "")).upper().strip()

    if not language or language != practice_language:
        raise ValueError(f"Teaching/practice language mismatch in {folder}")
    if not level or level != practice_level:
        raise ValueError(f"Teaching/practice level mismatch in {folder}")

    return teaching, practice


def _course_lesson(db: Session, teaching: dict, folder: Path) -> CourseLesson | None:
    language = str(teaching.get("language", "")).lower().strip()
    level = str(teaching.get("level", "")).upper().strip()

    try:
        lesson_order = int(teaching["lesson_order"])
    except (KeyError, TypeError, ValueError):
        try:
            lesson_order = int(folder.name.split("_")[-1])
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Cannot determine lesson order for {folder}") from exc

    return db.scalar(
        select(CourseLesson).where(
            CourseLesson.language == language,
            CourseLesson.level == level,
            CourseLesson.lesson_order == lesson_order,
        )
    )


def _content_payload(teaching: dict, practice: dict) -> dict:
    return {
        "format": "split_v1",
        "language": teaching.get("language"),
        "level": teaching.get("level"),
        "teaching": teaching,
        "practice": practice,
    }


def _upsert_content(db: Session, lesson: CourseLesson, teaching: dict, practice: dict) -> None:
    data = _content_payload(teaching, practice)
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
    existing.version = (existing.version or 0) + 1


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

    values = [str(pattern).strip() for pattern in patterns if str(pattern).strip()]
    suggestion = str(target_data.get("suggestion", "")).strip()
    if suggestion and suggestion not in values:
        values.append(suggestion)

    for value in values:
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
                    pattern_type="suggestion" if value == suggestion else "expected",
                )
            )


def _upsert_scenarios(
    db: Session,
    lesson: CourseLesson,
    practice: dict,
    targets_by_key: dict[str, LessonTarget],
) -> None:
    scenarios = practice.get("practice_scenarios")
    if not isinstance(scenarios, list):
        scenarios = practice.get("scenarios")
    if not isinstance(scenarios, list):
        scenarios = []

    conversation = practice.get("conversation")
    if not isinstance(conversation, dict):
        conversation = {}

    if not scenarios:
        scenarios = [
            {
                "id": "default",
                "order": 1,
                "title": "Lesson practice",
                "context": str(conversation.get("mode", "guided_natural")).strip(),
                "instructions": str(
                    conversation.get(
                        "rule",
                        "Use the lesson targets naturally in conversation.",
                    )
                ).strip(),
                "target_ids": list(targets_by_key.keys()),
            }
        ]

    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            continue

        key = str(
            scenario.get("id")
            or scenario.get("scenario_key")
            or f"scenario_{index}"
        ).strip()
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


def import_lesson(db: Session, folder: Path) -> bool:
    teaching, practice = _load_split_lesson(folder)
    lesson = _course_lesson(db, teaching, folder)
    if lesson is None:
        print(f"SKIP {folder}: CourseLesson not found")
        return False

    _upsert_content(db, lesson, teaching, practice)

    raw_targets = teaching.get("targets", [])
    if not isinstance(raw_targets, list):
        raw_targets = []

    targets_by_key: dict[str, LessonTarget] = {}
    for target_data in raw_targets:
        if not isinstance(target_data, dict):
            continue
        target = _upsert_target(db, lesson, target_data)
        _upsert_patterns(db, target, target_data)
        targets_by_key[target.target_key] = target

    practice_targets = practice.get("targets", [])
    if isinstance(practice_targets, list):
        for target_data in practice_targets:
            if not isinstance(target_data, dict):
                continue
            key = str(target_data.get("id", "")).strip()
            target = targets_by_key.get(key)
            if target is None:
                target = _upsert_target(db, lesson, target_data)
                targets_by_key[target.target_key] = target
            _upsert_patterns(db, target, target_data)

    _upsert_scenarios(db, lesson, practice, targets_by_key)
    return True


def sync_lesson_curriculum(db: Session) -> int:
    """Synchronize every split lesson folder into PostgreSQL."""
    imported = 0
    for folder in sorted(LESSONS_DIR.glob("*/*/lesson_*")):
        if not folder.is_dir():
            continue
        if not (folder / "teaching.json").exists() or not (folder / "practice.json").exists():
            continue
        if import_lesson(db, folder):
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
    print(f"Imported {imported} lesson curriculum folder(s).")


if __name__ == "__main__":
    main()
