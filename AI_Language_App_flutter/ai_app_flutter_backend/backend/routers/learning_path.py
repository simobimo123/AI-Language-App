import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LearningProfile,
    User,
    UserLessonProgress,
    SUPPORTED_LANGUAGE_CODES,
)
from routers.auth import get_current_user
from schemas import (
    CompleteLessonRequest,
    CompleteLessonResponse,
    LearningPathLessonResponse,
    LearningPathResponse,
)


router = APIRouter(
    prefix="/learning",
    tags=["Learning Path"],
)


LEVELS = [
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

SUPPORTED_LEARNING_LANGUAGES = list(SUPPORTED_LANGUAGE_CODES)


# =========================================================
# Lesson JSON configuration
# =========================================================
#
# The JSON curriculum is the single source of truth for:
# - lesson order
# - units
# - topic keys
# - test flags
# - passing scores
#
# We do NOT generate lesson JSON files automatically.
# Only JSON files that actually exist are synchronized.
#
LESSONS_ROOT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "lessons"
)


def _lesson_json_files(language: str, level: str) -> list[Path]:
    lesson_dir = LESSONS_ROOT / language / level

    if not lesson_dir.is_dir():
        return []

    return sorted(
        lesson_dir.glob("lesson_*.json"),
        key=lambda path: path.name,
    )


def _load_lesson_manifest(
    path: Path,
    expected_language: str,
    expected_level: str,
) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Invalid lesson JSON: {path} ({exc})"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Lesson JSON must contain an object: {path}"
        )

    language = str(data.get("language", "")).strip().lower()
    level = str(data.get("level", "")).strip().upper()
    lesson_order = data.get("lesson_order")

    if language != expected_language:
        raise RuntimeError(
            f"Lesson language mismatch in {path}: "
            f"expected '{expected_language}', got '{language}'."
        )

    if level != expected_level:
        raise RuntimeError(
            f"Lesson level mismatch in {path}: "
            f"expected '{expected_level}', got '{level}'."
        )

    if not isinstance(lesson_order, int) or lesson_order < 1:
        raise RuntimeError(
            f"Invalid lesson_order in {path}: {lesson_order!r}"
        )

    lesson_id = str(
        data.get("lesson_id")
        or f"{language}_{level.lower()}_lesson_{lesson_order:02d}"
    ).strip()

    topic_key = str(
        data.get("topic_key") or lesson_id
    ).strip()

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    is_test = bool(
        data.get("is_test", False)
        or metadata.get("is_test", False)
        or str(topic_key).lower() in {
            "level_test",
            "final_test",
            "pre_a1_final_test",
        }
    )

    unit_number = data.get("unit_number")

    if not isinstance(unit_number, int) or unit_number < 1:
        unit_number = metadata.get("unit_number")

    if not isinstance(unit_number, int) or unit_number < 1:
        unit_number = ((lesson_order - 1) // 2) + 1

    passing_score = data.get("passing_score")

    if not isinstance(passing_score, (int, float)):
        passing_score = metadata.get("passing_score")

    if not isinstance(passing_score, (int, float)):
        passing_score = 80.0

    return {
        "lesson_id": lesson_id,
        "language": language,
        "level": level,
        "lesson_order": lesson_order,
        "unit_number": unit_number,
        "topic_key": topic_key,
        "is_test": is_test,
        "passing_score": float(passing_score),
    }


def load_lesson_manifests(
    language: str,
    level: str,
) -> list[dict]:
    manifests: list[dict] = []
    seen_orders: set[int] = set()

    for path in _lesson_json_files(language, level):
        manifest = _load_lesson_manifest(
            path=path,
            expected_language=language,
            expected_level=level,
        )

        lesson_order = manifest["lesson_order"]

        if lesson_order in seen_orders:
            raise RuntimeError(
                f"Duplicate lesson_order {lesson_order} in "
                f"{language}/{level}."
            )

        seen_orders.add(lesson_order)
        manifests.append(manifest)

    manifests.sort(
        key=lambda item: item["lesson_order"]
    )

    return manifests


def sync_learning_content(
    language: str,
    level: str,
    db: Session,
) -> list[CourseLesson]:
    """
    Synchronize CourseLesson with the canonical lesson JSON files.

    JSON files are the source of truth.

    If no JSON files exist for a language/level, nothing is created.
    """

    manifests = load_lesson_manifests(
        language=language,
        level=level,
    )

    existing_lessons = (
        db.query(CourseLesson)
        .filter(
            CourseLesson.language == language,
            CourseLesson.level == level,
        )
        .order_by(CourseLesson.lesson_order.asc())
        .all()
    )

    existing_by_order = {
        lesson.lesson_order: lesson
        for lesson in existing_lessons
    }

    manifest_orders = {
        item["lesson_order"]
        for item in manifests
    }

    # Remove old database lessons that no longer exist
    # in the canonical JSON curriculum.
    for lesson in existing_lessons:
        if lesson.lesson_order not in manifest_orders:
            db.delete(lesson)

    # Create or update lessons from JSON.
    for manifest in manifests:
        lesson = existing_by_order.get(
            manifest["lesson_order"]
        )

        if lesson is None:
            lesson = CourseLesson(
                language=manifest["language"],
                level=manifest["level"],
                unit_number=manifest["unit_number"],
                lesson_order=manifest["lesson_order"],
                topic_key=manifest["topic_key"],
                is_test=manifest["is_test"],
                passing_score=manifest["passing_score"],
            )

            db.add(lesson)
            existing_by_order[
                manifest["lesson_order"]
            ] = lesson

            continue

        lesson.language = manifest["language"]
        lesson.level = manifest["level"]
        lesson.unit_number = manifest["unit_number"]
        lesson.topic_key = manifest["topic_key"]
        lesson.is_test = manifest["is_test"]
        lesson.passing_score = manifest["passing_score"]

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to synchronize learning curriculum.",
        ) from exc

    return (
        db.query(CourseLesson)
        .filter(
            CourseLesson.language == language,
            CourseLesson.level == level,
        )
        .order_by(
            CourseLesson.lesson_order.asc()
        )
        .all()
    )


def seed_learning_content(db: Session) -> None:
    """
    Synchronize all existing lesson JSON curricula at startup.

    This function does NOT create lesson JSON files.

    It only imports lesson metadata from JSON files that already
    exist under:

        data/lessons/<language>/<level>/

    Missing language/level directories are simply ignored.
    """

    synchronized = 0

    for language in SUPPORTED_LEARNING_LANGUAGES:
        for level in LEVELS:
            lesson_files = _lesson_json_files(
                language,
                level,
            )

            if not lesson_files:
                continue

            sync_learning_content(
                language=language,
                level=level,
                db=db,
            )

            synchronized += 1

    print(
        f"Learning curriculum synchronization completed. "
        f"Curricula synchronized: {synchronized}"
    )


def normalize_language(language: str) -> str:
    normalized = language.strip().lower()

    if normalized not in SUPPORTED_LEARNING_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported learning language "
                f"'{normalized}'."
            ),
        )

    return normalized


def normalize_level(level: str) -> str:
    normalized = level.strip().upper()

    if normalized not in LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported learning level "
                f"'{normalized}'."
            ),
        )

    return normalized


def get_next_level(level: str) -> str | None:
    try:
        index = LEVELS.index(level)
    except ValueError:
        return None

    if index >= len(LEVELS) - 1:
        return None

    return LEVELS[index + 1]


def get_previous_level(level: str) -> str:
    try:
        index = LEVELS.index(level)
    except ValueError:
        return "PRE_A1"

    if index <= 0:
        return "PRE_A1"

    return LEVELS[index - 1]


def get_current_profile(
    current_user: User,
    db: Session,
) -> LearningProfile:
    language = normalize_language(
        current_user.learning_language
    )

    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == language,
        )
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Current learning profile not found.",
        )

    return profile


def get_progress_map(
    user_id: int,
    profile_id: int,
    lesson_ids: list[int],
    db: Session,
) -> dict[int, UserLessonProgress]:
    if not lesson_ids:
        return {}

    progress_records = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.learning_profile_id
            == profile_id,
            UserLessonProgress.lesson_id.in_(
                lesson_ids
            ),
        )
        .all()
    )

    return {
        item.lesson_id: item
        for item in progress_records
    }


def calculate_normal_progress(
    normal_lessons: list[CourseLesson],
    progress_map: dict[int, UserLessonProgress],
) -> float:
    if not normal_lessons:
        return 0.0

    completed_count = sum(
        1
        for lesson in normal_lessons
        if (
            progress_map.get(lesson.id)
            and progress_map[lesson.id].completed
        )
    )

    return (
        completed_count
        / len(normal_lessons)
        * 100.0
    )


def get_or_create_lesson_progress(
    current_user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    db: Session,
) -> UserLessonProgress:
    progress = (
        db.query(UserLessonProgress)
        .filter(
            UserLessonProgress.user_id
            == current_user.id,
            UserLessonProgress.lesson_id
            == lesson.id,
        )
        .first()
    )

    if progress is not None:
        if progress.learning_profile_id != profile.id:
            progress.learning_profile_id = profile.id

        return progress

    progress = UserLessonProgress(
        user_id=current_user.id,
        learning_profile_id=profile.id,
        lesson_id=lesson.id,
        completed=False,
        best_score=0.0,
        attempts=0,
    )

    db.add(progress)

    return progress


def get_current_lesson(
    lessons: list[CourseLesson],
    progress_map: dict[int, UserLessonProgress],
) -> CourseLesson | None:
    normal_lessons = [
        lesson
        for lesson in lessons
        if not lesson.is_test
    ]

    for lesson in normal_lessons:
        progress = progress_map.get(lesson.id)

        if progress is None or not progress.completed:
            return lesson

    for lesson in lessons:
        if lesson.is_test:
            progress = progress_map.get(lesson.id)

            if progress is None or not progress.completed:
                return lesson

    return None


@router.get(
    "/path",
    response_model=LearningPathResponse,
)
def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_current_profile(
        current_user,
        db,
    )

    try:
        lessons = sync_learning_content(
            language=profile.language,
            level=profile.level,
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if not lessons:
        raise HTTPException(
            status_code=404,
            detail=(
                "No lesson JSON files found for "
                f"{profile.language}/{profile.level}."
            ),
        )

    lesson_ids = [
        lesson.id
        for lesson in lessons
    ]

    progress_map = get_progress_map(
        user_id=current_user.id,
        profile_id=profile.id,
        lesson_ids=lesson_ids,
        db=db,
    )

    normal_lessons = [
        lesson
        for lesson in lessons
        if not lesson.is_test
    ]

    calculated_progress = calculate_normal_progress(
        normal_lessons,
        progress_map,
    )

    if round(profile.progress, 4) != round(
        calculated_progress,
        4,
    ):
        profile.progress = calculated_progress
        db.commit()

    current_lesson = get_current_lesson(
        lessons=lessons,
        progress_map=progress_map,
    )

    completed_normal = sum(
        1
        for lesson in normal_lessons
        if (
            progress_map.get(lesson.id)
            and progress_map[lesson.id].completed
        )
    )

    total_normal = len(normal_lessons)

    path_lessons = []

    for lesson in lessons:
        progress = progress_map.get(lesson.id)

        completed = (
            progress.completed
            if progress
            else False
        )

        best_score = (
            progress.best_score
            if progress
            else 0.0
        )

        attempts = (
            progress.attempts
            if progress
            else 0
        )

        if completed:
            status = "completed"

        elif (
            current_lesson is not None
            and lesson.id == current_lesson.id
        ):
            status = "current"

        else:
            status = "locked"

        path_lessons.append(
            LearningPathLessonResponse(
                id=lesson.id,
                language=lesson.language,
                level=lesson.level,
                unit_number=lesson.unit_number,
                lesson_order=lesson.lesson_order,
                topic_key=lesson.topic_key,
                is_test=lesson.is_test,
                passing_score=lesson.passing_score,
                status=status,
                completed=completed,
                best_score=best_score,
                attempts=attempts,
            )
        )

    return LearningPathResponse(
        language=profile.language,
        level=profile.level,
        progress=round(
            calculated_progress,
            2,
        ),
        completed_lessons=completed_normal,
        total_lessons=total_normal,
        next_level=get_next_level(
            profile.level
        ),
        lessons=path_lessons,
    )


@router.post(
    "/lessons/{lesson_id}/complete",
    response_model=CompleteLessonResponse,
)
def complete_lesson(
    lesson_id: int,
    data: CompleteLessonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_current_profile(
        current_user,
        db,
    )

    try:
        all_lessons = sync_learning_content(
            language=profile.language,
            level=profile.level,
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    lesson = next(
        (
            item
            for item in all_lessons
            if item.id == lesson_id
        ),
        None,
    )

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Lesson not found in the current "
                "curriculum."
            ),
        )

    if not all_lessons:
        raise HTTPException(
            status_code=404,
            detail=(
                "No learning lessons found for the "
                "current level."
            ),
        )

    lesson_ids = [
        item.id
        for item in all_lessons
    ]

    progress_map = get_progress_map(
        user_id=current_user.id,
        profile_id=profile.id,
        lesson_ids=lesson_ids,
        db=db,
    )

    current_lesson = get_current_lesson(
        lessons=all_lessons,
        progress_map=progress_map,
    )

    if current_lesson is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "All lessons in this level are "
                "already completed."
            ),
        )

    if current_lesson.id != lesson.id:
        raise HTTPException(
            status_code=400,
            detail=(
                "This lesson is currently locked. "
                "Complete the previous lessons first."
            ),
        )

    lesson_progress = progress_map.get(
        lesson.id
    )

    if lesson_progress is None:
        lesson_progress = (
            get_or_create_lesson_progress(
                current_user=current_user,
                profile=profile,
                lesson=lesson,
                db=db,
            )
        )

    if lesson_progress.completed:
        raise HTTPException(
            status_code=400,
            detail=(
                "This lesson has already been "
                "completed."
            ),
        )

    lesson_progress.attempts += 1

    if data.score > lesson_progress.best_score:
        lesson_progress.best_score = data.score

    old_level = profile.level
    level_upgraded = False
    new_level = old_level

    if not lesson.is_test:
        lesson_progress.completed = True
        lesson_progress.completed_at = datetime.utcnow()

    else:
        normal_lessons = [
            item
            for item in all_lessons
            if not item.is_test
        ]

        normal_ids = {
            item.id
            for item in normal_lessons
        }

        completed_ids = {
            progress.lesson_id
            for progress in progress_map.values()
            if (
                progress.completed
                and progress.lesson_id
                in normal_ids
            )
        }

        missing_lessons = (
            normal_ids - completed_ids
        )

        if missing_lessons:
            raise HTTPException(
                status_code=400,
                detail=(
                    "You must complete all normal "
                    "lessons before taking the "
                    "level test."
                ),
            )

        if data.score < lesson.passing_score:
            lesson_progress.completed = False

            profile.progress = (
                calculate_normal_progress(
                    normal_lessons,
                    progress_map,
                )
            )

            db.commit()

            return CompleteLessonResponse(
                message=(
                    "Level test was not passed."
                ),
                lesson_id=lesson.id,
                completed=False,
                score=data.score,
                level_upgraded=False,
                old_level=old_level,
                new_level=old_level,
                new_progress=round(
                    profile.progress,
                    2,
                ),
            )

        lesson_progress.completed = True
        lesson_progress.completed_at = datetime.utcnow()

        next_level = get_next_level(
            profile.level
        )

        if next_level is not None:
            profile.level = next_level
            profile.progress = 0.0
            new_level = next_level
            level_upgraded = True

        else:
            profile.progress = 100.0

    if not level_upgraded:
        normal_lessons = [
            item
            for item in all_lessons
            if not item.is_test
        ]

        progress_map[
            lesson_progress.lesson_id
        ] = lesson_progress

        profile.progress = (
            calculate_normal_progress(
                normal_lessons,
                progress_map,
            )
        )

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Unable to save lesson progress.",
        ) from exc

    db.refresh(profile)
    db.refresh(lesson_progress)

    return CompleteLessonResponse(
        message=(
            "Lesson completed successfully"
            if lesson_progress.completed
            else (
                "Lesson completed but the level "
                "test was not passed"
            )
        ),
        lesson_id=lesson.id,
        completed=lesson_progress.completed,
        score=data.score,
        level_upgraded=level_upgraded,
        old_level=old_level,
        new_level=new_level,
        new_progress=round(
            profile.progress,
            2,
        ),
    )