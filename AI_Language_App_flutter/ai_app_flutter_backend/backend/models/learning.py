from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


from .base import Base


class CourseLesson(Base):
    __tablename__ = "course_lessons"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    unit_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    lesson_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    topic_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    is_test: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    passing_score: Mapped[float] = mapped_column(
        Float,
        default=80.0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "language",
            "level",
            "lesson_order",
            name="uq_course_lesson_language_level_order"
        ),
    )


# =========================================================
# User Lesson Progress
# =========================================================

class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "learning_profiles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey(
            "course_lessons.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    best_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lesson_id",
            name="uq_user_lesson_progress"
        ),
    )


# =========================================================
# User Learning Bank Item
# =========================================================

class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # Existing API keeps this field name for backward compatibility.
    # For item_type="word" it contains the word; for item_type="sentence"
    # it contains the complete sentence.
    word: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    translation: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    item_type: Mapped[str] = mapped_column(
        String(20),
        default="word",
        nullable=False,
        index=True
    )

    learned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "learning_profiles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    vocabulary_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_entries.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    vocabulary_form_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_forms.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "learning_profile_id",
            "vocabulary_form_id",
            name="uq_word_user_profile_form"
        ),
    )


# =========================================================
# AI Usage
# =========================================================
