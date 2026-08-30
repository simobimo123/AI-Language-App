from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AIConversationMessage,
    CourseLesson,
    LearningProfile,
    User,
    UserLessonProgress,
    Word,
)
from routers.auth import get_current_user
from schemas import HomeStatsResponse


router = APIRouter(
    prefix="/stats",
    tags=["Statistics"],
)


# =========================================================
# Helpers
# =========================================================

def calculate_streak(
    activity_dates: set[date],
) -> int:
    if not activity_dates:
        return 0

    today = date.today()

    # A current streak must contain today or yesterday.
    if today in activity_dates:
        current_date = today

    elif (today - timedelta(days=1)) in activity_dates:
        current_date = today - timedelta(days=1)

    else:
        return 0

    streak = 0

    while current_date in activity_dates:
        streak += 1
        current_date -= timedelta(days=1)

    return streak


# =========================================================
# Home statistics
# =========================================================

@router.get(
    "",
    response_model=HomeStatsResponse,
)
def get_home_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # =====================================================
    # Current learning profile
    # =====================================================

    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language
            == current_user.learning_language,
        )
        .first()
    )

    learning_progress = 0.0
    completed_lessons = 0
    total_lessons = 0

    if profile is not None:
        # -------------------------------------------------
        # Learning progress
        # -------------------------------------------------

        learning_progress = float(
            profile.progress or 0.0
        )

        # -------------------------------------------------
        # Completed lessons
        # -------------------------------------------------

        completed_lessons = (
            db.query(UserLessonProgress)
            .filter(
                UserLessonProgress.user_id
                == current_user.id,
                UserLessonProgress.learning_profile_id
                == profile.id,
                UserLessonProgress.completed.is_(True),
            )
            .count()
        )

        # -------------------------------------------------
        # Total normal lessons
        #
        # Level tests are excluded because the learning
        # path itself treats normal lessons separately.
        # -------------------------------------------------

        total_lessons = (
            db.query(CourseLesson)
            .filter(
                CourseLesson.language
                == profile.language,
                CourseLesson.level
                == profile.level,
                CourseLesson.is_test.is_(False),
            )
            .count()
        )

    # =====================================================
    # Learned words
    # =====================================================

    learned_words = (
        db.query(Word)
        .filter(
            Word.user_id == current_user.id,
            Word.learned.is_(True),
        )
        .count()
    )

    # =====================================================
    # AI conversations
    # =====================================================

    conversation_ids = (
        db.query(
            AIConversationMessage.conversation_id
        )
        .filter(
            AIConversationMessage.user_id
            == current_user.id,
            AIConversationMessage.conversation_id
            .isnot(None),
        )
        .distinct()
        .all()
    )

    conversations = len(conversation_ids)

    # =====================================================
    # Activity dates
    #
    # Used for the current learning streak.
    # A day counts as active when the user:
    #
    # - completes a lesson
    # - saves/creates a word
    # - participates in an AI conversation
    # =====================================================

    activity_dates: set[date] = set()

    # -----------------------------------------------------
    # Completed lesson activity
    # -----------------------------------------------------

    lesson_activity = (
        db.query(
            UserLessonProgress.completed_at
        )
        .filter(
            UserLessonProgress.user_id
            == current_user.id,
            UserLessonProgress.completed.is_(True),
            UserLessonProgress.completed_at
            .isnot(None),
        )
        .all()
    )

    for (completed_at,) in lesson_activity:
        if completed_at is not None:
            activity_dates.add(
                completed_at.date()
            )

    # -----------------------------------------------------
    # Word activity
    # -----------------------------------------------------

    word_activity = (
        db.query(
            Word.created_at
        )
        .filter(
            Word.user_id == current_user.id,
            Word.created_at.isnot(None),
        )
        .all()
    )

    for (created_at,) in word_activity:
        if created_at is not None:
            activity_dates.add(
                created_at.date()
            )

    # -----------------------------------------------------
    # AI conversation activity
    # -----------------------------------------------------

    ai_activity = (
        db.query(
            AIConversationMessage.created_at
        )
        .filter(
            AIConversationMessage.user_id
            == current_user.id,
            AIConversationMessage.created_at
            .isnot(None),
        )
        .all()
    )

    for (created_at,) in ai_activity:
        if created_at is not None:
            activity_dates.add(
                created_at.date()
            )

    # =====================================================
    # Streak
    # =====================================================

    streak_days = calculate_streak(
        activity_dates
    )

    # =====================================================
    # Response
    # =====================================================

    return HomeStatsResponse(
        streak_days=streak_days,
        learned_words=learned_words,
        conversations=conversations,
        learning_progress=round(
            learning_progress,
            2,
        ),
        completed_lessons=completed_lessons,
        total_lessons=total_lessons,
    )