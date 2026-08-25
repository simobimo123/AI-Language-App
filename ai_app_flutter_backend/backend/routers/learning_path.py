from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LearningProfile,
    User,
    UserLessonProgress,
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


# =========================================================
# Learning levels
# =========================================================

LEVELS = [
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]


# =========================================================
# Vocabulary / learning languages
# =========================================================
#
# These are the 20 languages supported by the global
# vocabulary architecture.
#
# The learning-path system can support all of them, but
# actual course content is still generated from LEVEL_TOPICS.
# Later, each language can receive language-specific
# curriculum content.
# =========================================================

SUPPORTED_LEARNING_LANGUAGES = [
    "ar",
    "de",
    "en",
    "es",
    "fa",
    "fr",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "th",
    "tr",
    "uk",
    "vi",
    "zh",
]


# =========================================================
# Course content template
# =========================================================

LEVEL_TOPICS = {
    # -----------------------------------------------------
    # PRE_A1
    # -----------------------------------------------------

    "PRE_A1": [
        ("sounds_and_letters", 1),
        ("basic_greetings", 2),
        ("numbers_0_10", 3),
        ("colors", 4),
        ("family_basics", 5),
        ("everyday_objects", 6),
        ("very_basic_phrases", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # A1
    # -----------------------------------------------------

    "A1": [
        ("alphabet", 1),
        ("basic_words", 2),
        ("numbers", 3),
        ("greetings", 4),
        ("introductions", 5),
        ("family", 6),
        ("simple_sentences", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # A2
    # -----------------------------------------------------

    "A2": [
        ("daily_life", 1),
        ("past_tense", 2),
        ("future", 3),
        ("shopping", 4),
        ("travel", 5),
        ("health", 6),
        ("describing_people", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # B1
    # -----------------------------------------------------

    "B1": [
        ("daily_conversations", 1),
        ("telling_stories", 2),
        ("work", 3),
        ("opinions", 4),
        ("social_situations", 5),
        ("media", 6),
        ("extended_conversations", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # B2
    # -----------------------------------------------------

    "B2": [
        ("debates", 1),
        ("arguments", 2),
        ("complex_vocabulary", 3),
        ("idioms", 4),
        ("workplace", 5),
        ("problem_solving", 6),
        ("presentations", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # C1
    # -----------------------------------------------------

    "C1": [
        ("language_nuance", 1),
        ("advanced_grammar", 2),
        ("formal_speech", 3),
        ("academic_language", 4),
        ("professional_language", 5),
        ("culture", 6),
        ("critical_discussion", 7),
        ("level_test", 8),
    ],

    # -----------------------------------------------------
    # C2
    # -----------------------------------------------------

    "C2": [
        ("language_mastery", 1),
        ("rhetoric", 2),
        ("advanced_idioms", 3),
        ("language_register", 4),
        ("complex_debates", 5),
        ("interpretation", 6),
        ("fluency", 7),
        ("level_test", 8),
    ],
}


# =========================================================
# Normalization helpers
# =========================================================

def normalize_language(
    language: str,
) -> str:

    normalized = (
        language
        .strip()
        .lower()
    )

    if normalized not in SUPPORTED_LEARNING_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported learning language "
                f"'{normalized}'."
            ),
        )

    return normalized


def normalize_level(
    level: str,
) -> str:

    normalized = (
        level
        .strip()
        .upper()
    )

    if normalized not in LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported learning level "
                f"'{normalized}'."
            ),
        )

    return normalized


# =========================================================
# Course content seeding
# =========================================================
#
# This function is idempotent.
#
# Unlike the old implementation, it only commits when
# something was actually created.
#
# It still uses the current template-based curriculum.
# Later we can replace this with language-specific lesson
# content stored in the database.
# =========================================================

def seed_learning_content(
    db: Session,
) -> None:

    created_any = False

    for language in SUPPORTED_LEARNING_LANGUAGES:

        for level in LEVELS:

            topics = LEVEL_TOPICS[
                level
            ]

            for index, (
                topic_key,
                lesson_order,
            ) in enumerate(
                topics
            ):

                existing = (
                    db.query(
                        CourseLesson
                    )
                    .filter(
                        CourseLesson.language
                        == language,
                        CourseLesson.level
                        == level,
                        CourseLesson.lesson_order
                        == lesson_order,
                    )
                    .first()
                )

                if existing is not None:
                    continue

                is_test = (
                    topic_key
                    == "level_test"
                )

                lesson = CourseLesson(
                    language=language,
                    level=level,
                    unit_number=(
                        index // 2
                    ) + 1,
                    lesson_order=lesson_order,
                    topic_key=topic_key,
                    is_test=is_test,
                    passing_score=80.0,
                )

                db.add(lesson)

                created_any = True

    if created_any:

        try:
            db.commit()

        except IntegrityError:
            db.rollback()

            # A concurrent startup/request may have created
            # the same lesson. This is safe to ignore here.
            #
            # The database unique constraint is the final
            # protection against duplicates.
            pass


# =========================================================
# Level helpers
# =========================================================

def get_next_level(
    level: str,
) -> str | None:

    try:
        index = LEVELS.index(
            level
        )

    except ValueError:
        return None

    if index >= len(LEVELS) - 1:
        return None

    return LEVELS[
        index + 1
    ]


def get_previous_level(
    level: str,
) -> str:

    try:
        index = LEVELS.index(
            level
        )

    except ValueError:
        return "PRE_A1"

    if index <= 0:
        return "PRE_A1"

    return LEVELS[
        index - 1
    ]


# =========================================================
# Current profile
# =========================================================

def get_current_profile(
    current_user: User,
    db: Session,
) -> LearningProfile:

    language = normalize_language(
        current_user.learning_language
    )

    profile = (
        db.query(
            LearningProfile
        )
        .filter(
            LearningProfile.user_id
            == current_user.id,
            LearningProfile.language
            == language,
        )
        .first()
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Current learning profile not found."
            ),
        )

    return profile


# =========================================================
# Progress helpers
# =========================================================

def get_progress_map(
    user_id: int,
    profile_id: int,
    lesson_ids: list[int],
    db: Session,
) -> dict[int, UserLessonProgress]:

    if not lesson_ids:
        return {}

    progress_records = (
        db.query(
            UserLessonProgress
        )
        .filter(
            UserLessonProgress.user_id
            == user_id,
            UserLessonProgress.learning_profile_id
            == profile_id,
            UserLessonProgress.lesson_id
            .in_(lesson_ids),
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
            progress_map.get(
                lesson.id
            )
            and progress_map[
                lesson.id
            ].completed
        )
    )

    return (
        completed_count
        / len(normal_lessons)
        * 100.0
    )


# =========================================================
# Ensure progress record
# =========================================================

def get_or_create_lesson_progress(
    current_user: User,
    profile: LearningProfile,
    lesson: CourseLesson,
    db: Session,
) -> UserLessonProgress:

    progress = (
        db.query(
            UserLessonProgress
        )
        .filter(
            UserLessonProgress.user_id
            == current_user.id,
            UserLessonProgress.lesson_id
            == lesson.id,
        )
        .first()
    )

    if progress is not None:

        # Keep the profile relation correct.
        if (
            progress.learning_profile_id
            != profile.id
        ):
            progress.learning_profile_id = (
                profile.id
            )

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


# =========================================================
# Determine the current lesson
# =========================================================

def get_current_lesson(
    lessons: list[CourseLesson],
    progress_map: dict[int, UserLessonProgress],
) -> CourseLesson | None:

    normal_lessons = [
        lesson
        for lesson in lessons
        if not lesson.is_test
    ]

    # -----------------------------------------------------
    # First incomplete normal lesson.
    # -----------------------------------------------------

    for lesson in normal_lessons:

        progress = progress_map.get(
            lesson.id
        )

        if (
            progress is None
            or not progress.completed
        ):
            return lesson

    # -----------------------------------------------------
    # If every normal lesson is complete, the level test
    # becomes the current lesson.
    # -----------------------------------------------------

    for lesson in lessons:

        if lesson.is_test:

            progress = progress_map.get(
                lesson.id
            )

            if (
                progress is None
                or not progress.completed
            ):
                return lesson

    return None


# =========================================================
# Get current learning path
# =========================================================

@router.get(
    "/path",
    response_model=LearningPathResponse,
)
def get_learning_path(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    seed_learning_content(
        db
    )

    profile = get_current_profile(
        current_user,
        db,
    )

    lessons = (
        db.query(
            CourseLesson
        )
        .filter(
            CourseLesson.language
            == profile.language,
            CourseLesson.level
            == profile.level,
        )
        .order_by(
            CourseLesson.lesson_order.asc()
        )
        .all()
    )

    if not lessons:

        raise HTTPException(
            status_code=404,
            detail=(
                "No learning content found for "
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

    # Keep profile.progress synchronized with the actual
    # lesson records.
    if (
        round(
            profile.progress,
            4,
        )
        != round(
            calculated_progress,
            4,
        )
    ):
        profile.progress = (
            calculated_progress
        )
        db.commit()

    current_lesson = get_current_lesson(
        lessons=lessons,
        progress_map=progress_map,
    )

    completed_normal = sum(
        1
        for lesson in normal_lessons
        if (
            progress_map.get(
                lesson.id
            )
            and progress_map[
                lesson.id
            ].completed
        )
    )

    total_normal = len(
        normal_lessons
    )

    path_lessons = []

    for lesson in lessons:

        progress = progress_map.get(
            lesson.id
        )

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
            and lesson.id
            == current_lesson.id
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


# =========================================================
# Complete lesson
# =========================================================

@router.post(
    "/lessons/{lesson_id}/complete",
    response_model=CompleteLessonResponse,
)
def complete_lesson(
    lesson_id: int,
    data: CompleteLessonRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    seed_learning_content(
        db
    )

    profile = get_current_profile(
        current_user,
        db,
    )

    # -----------------------------------------------------
    # Load the lesson only from the user's current language
    # and current level.
    # -----------------------------------------------------

    lesson = (
        db.query(
            CourseLesson
        )
        .filter(
            CourseLesson.id == lesson_id,
            CourseLesson.language
            == profile.language,
            CourseLesson.level
            == profile.level,
        )
        .first()
    )

    if lesson is None:

        raise HTTPException(
            status_code=404,
            detail="Lesson not found.",
        )

    # -----------------------------------------------------
    # Load ALL lessons for the current level.
    # -----------------------------------------------------

    all_lessons = (
        db.query(
            CourseLesson
        )
        .filter(
            CourseLesson.language
            == profile.language,
            CourseLesson.level
            == profile.level,
        )
        .order_by(
            CourseLesson.lesson_order.asc()
        )
        .all()
    )

    if not all_lessons:

        raise HTTPException(
            status_code=404,
            detail=(
                "No learning lessons found "
                "for the current level."
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

    # =====================================================
    # SECURITY / LOGIC CHECK:
    #
    # A user cannot complete an arbitrary locked lesson.
    #
    # Determine the lesson that is actually current.
    # =====================================================

    current_lesson = get_current_lesson(
        lessons=all_lessons,
        progress_map=progress_map,
    )

    if current_lesson is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "All lessons in this level "
                "are already completed."
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

    # =====================================================
    # Get or create progress record
    # =====================================================

    lesson_progress = (
        progress_map.get(
            lesson.id
        )
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

    # -----------------------------------------------------
    # A lesson that was already completed is not allowed to
    # be completed again through this endpoint.
    #
    # Retakes can later be implemented through a dedicated
    # assessment endpoint.
    # -----------------------------------------------------

    if lesson_progress.completed:

        raise HTTPException(
            status_code=400,
            detail=(
                "This lesson has already been completed."
            ),
        )

    lesson_progress.attempts += 1

    if (
        data.score
        > lesson_progress.best_score
    ):
        lesson_progress.best_score = (
            data.score
        )

    old_level = profile.level
    level_upgraded = False
    new_level = old_level

    # =====================================================
    # Normal lesson
    # =====================================================

    if not lesson.is_test:

        lesson_progress.completed = True

        lesson_progress.completed_at = (
            datetime.utcnow()
        )

    # =====================================================
    # Level test
    # =====================================================

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
            normal_ids
            - completed_ids
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

        # -------------------------------------------------
        # The test itself requires the configured score.
        # -------------------------------------------------

        if data.score < lesson.passing_score:

            lesson_progress.completed = False

            # The user's level does not change.
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

        # -------------------------------------------------
        # Level test passed.
        # -------------------------------------------------

        lesson_progress.completed = True

        lesson_progress.completed_at = (
            datetime.utcnow()
        )

        next_level = get_next_level(
            profile.level
        )

        if next_level is not None:

            # The current level is finished.
            #
            # The user moves to the next level.
            profile.level = next_level

            profile.progress = 0.0

            new_level = next_level

            level_upgraded = True

        else:

            # C2 is the final level.
            profile.progress = 100.0

    # =====================================================
    # Normal lesson progress update
    # =====================================================

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

    # =====================================================
    # Persist everything
    # =====================================================

    try:

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to save lesson progress."
            ),
        )

    db.refresh(profile)
    db.refresh(lesson_progress)

    return CompleteLessonResponse(
        message=(
            "Lesson completed successfully"
            if lesson_progress.completed
            else "Lesson completed but the "
                 "level test was not passed"
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