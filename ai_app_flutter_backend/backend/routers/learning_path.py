from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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
#
# PRE_A1 is the beginner level before A1.
#
# Order:
#
# PRE_A1 -> A1 -> A2 -> B1 -> B2 -> C1 -> C2
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


SUPPORTED_LEARNING_LANGUAGES = [
    "ar",
    "en",
    "fr",
    "es",
    "de",
    "tr",
]


# =========================================================
# Course content
# =========================================================

LEVEL_TOPICS = {
    # -----------------------------------------------------
    # PRE-A1
    # -----------------------------------------------------
    #
    # This level is for complete beginners.
    #
    # We intentionally avoid making it dependent on one
    # specific writing system because the application
    # supports multiple languages.
    #
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


def seed_learning_content(
    db: Session,
) -> None:
    """
    ينشئ محتوى المسار الأساسي مرة واحدة.
    إذا كان موجودًا، لا ينشئ نسخًا أخرى.

    PRE_A1 أصبح الآن مستوى حقيقيًا مثل بقية المستويات.
    """

    for language in SUPPORTED_LEARNING_LANGUAGES:
        for level in LEVELS:
            topics = LEVEL_TOPICS[level]

            for index, (topic_key, lesson_order) in enumerate(
                topics
            ):
                existing = db.query(CourseLesson).filter(
                    CourseLesson.language == language,
                    CourseLesson.level == level,
                    CourseLesson.lesson_order == lesson_order,
                ).first()

                if existing:
                    continue

                is_test = topic_key == "level_test"

                lesson = CourseLesson(
                    language=language,
                    level=level,
                    unit_number=((index) // 2) + 1,
                    lesson_order=lesson_order,
                    topic_key=topic_key,
                    is_test=is_test,
                    passing_score=80.0,
                )

                db.add(lesson)

    db.commit()


# =========================================================
# Helpers
# =========================================================

def get_next_level(level: str) -> str | None:
    try:
        index = LEVELS.index(level)
    except ValueError:
        return None

    if index >= len(LEVELS) - 1:
        return None

    return LEVELS[index + 1]


def get_current_profile(
    current_user: User,
    db: Session,
) -> LearningProfile:

    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language ==
            current_user.learning_language,
    ).first()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Current learning profile not found",
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

    progress_records = db.query(
        UserLessonProgress
    ).filter(
        UserLessonProgress.user_id == user_id,
        UserLessonProgress.learning_profile_id == profile_id,
        UserLessonProgress.lesson_id.in_(lesson_ids),
    ).all()

    return {
        item.lesson_id: item
        for item in progress_records
    }


# =========================================================
# Get current learning path
# =========================================================

@router.get(
    "/path",
    response_model=LearningPathResponse,
)
def get_learning_path(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    seed_learning_content(db)

    profile = get_current_profile(
        current_user,
        db,
    )

    lessons = db.query(CourseLesson).filter(
        CourseLesson.language ==
            profile.language,
        CourseLesson.level ==
            profile.level,
    ).order_by(
        CourseLesson.lesson_order.asc()
    ).all()

    lesson_ids = [
        lesson.id
        for lesson in lessons
    ]

    progress_map = get_progress_map(
        current_user.id,
        profile.id,
        lesson_ids,
        db,
    )

    normal_lessons = [
        lesson
        for lesson in lessons
        if not lesson.is_test
    ]

    completed_normal = 0

    for lesson in normal_lessons:
        progress = progress_map.get(lesson.id)

        if progress and progress.completed:
            completed_normal += 1

    total_normal = len(normal_lessons)

    if total_normal > 0:
        calculated_progress = (
            completed_normal / total_normal
        ) * 100
    else:
        calculated_progress = 0.0

    profile.progress = calculated_progress

    # أول درس غير مكتمل هو الدرس الحالي.
    current_found = False
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

        elif not current_found:
            # اختبار المستوى لا يصبح متاحًا
            # إلا بعد إنهاء جميع الدروس العادية.
            if lesson.is_test and (
                completed_normal < total_normal
            ):
                status = "locked"
            else:
                status = "current"

            current_found = True

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

    db.commit()

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    seed_learning_content(db)

    profile = get_current_profile(
        current_user,
        db,
    )

    lesson = db.query(CourseLesson).filter(
        CourseLesson.id == lesson_id,
        CourseLesson.language ==
            profile.language,
        CourseLesson.level ==
            profile.level,
    ).first()

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="Lesson not found",
        )

    all_lessons = db.query(CourseLesson).filter(
        CourseLesson.language ==
            profile.language,
        CourseLesson.level ==
            profile.level,
    ).order_by(
        CourseLesson.lesson_order.asc()
    ).all()

    lesson_progress = db.query(
        UserLessonProgress
    ).filter(
        UserLessonProgress.user_id ==
            current_user.id,
        UserLessonProgress.lesson_id ==
            lesson_id,
    ).first()

    if lesson_progress is None:
        lesson_progress = UserLessonProgress(
            user_id=current_user.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            completed=False,
            best_score=0.0,
            attempts=0,
        )

        db.add(lesson_progress)

    lesson_progress.attempts += 1

    if data.score > lesson_progress.best_score:
        lesson_progress.best_score = data.score

    old_level = profile.level
    level_upgraded = False
    new_level = old_level

    # =====================================================
    # Normal lesson
    # =====================================================

    if not lesson.is_test:
        lesson_progress.completed = True
        lesson_progress.completed_at = datetime.utcnow()

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

        completed_progress = db.query(
            UserLessonProgress
        ).filter(
            UserLessonProgress.user_id ==
                current_user.id,
            UserLessonProgress.lesson_id.in_(
                normal_ids
            ),
            UserLessonProgress.completed.is_(True),
        ).all()

        completed_ids = {
            item.lesson_id
            for item in completed_progress
        }

        missing_lessons = (
            normal_ids - completed_ids
        )

        if missing_lessons:
            raise HTTPException(
                status_code=400,
                detail=(
                    "You must complete all lessons "
                    "before taking the level test"
                ),
            )

        if data.score >= lesson.passing_score:
            lesson_progress.completed = True
            lesson_progress.completed_at = (
                datetime.utcnow()
            )

            next_level = get_next_level(
                profile.level
            )

            if next_level is not None:
                profile.level = next_level
                profile.progress = 0.0

                new_level = next_level
                level_upgraded = True
            else:
                # C2 هو المستوى الأخير.
                profile.progress = 100.0

        else:
            lesson_progress.completed = False

    # =====================================================
    # Update progress
    # =====================================================

    if not level_upgraded:
        normal_lessons = [
            item
            for item in all_lessons
            if not item.is_test
        ]

        if normal_lessons:
            normal_ids = {
                item.id
                for item in normal_lessons
            }

            completed_count = db.query(
                UserLessonProgress
            ).filter(
                UserLessonProgress.user_id ==
                    current_user.id,
                UserLessonProgress.lesson_id.in_(
                    normal_ids
                ),
                UserLessonProgress.completed.is_(True),
            ).count()

            profile.progress = (
                completed_count /
                len(normal_lessons)
            ) * 100
        else:
            profile.progress = 0.0

    db.commit()

    return CompleteLessonResponse(
        message=(
            "Lesson completed successfully"
            if lesson_progress.completed
            else "Lesson completed but level test was not passed"
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