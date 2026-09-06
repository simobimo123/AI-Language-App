from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserLessonStageProgress(Base):
    """Persistent state for the three independent stages of a lesson."""

    __tablename__ = "user_lesson_stage_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    learn_status: Mapped[str] = mapped_column(
        String(20), default="available", nullable=False
    )
    teaching_status: Mapped[str] = mapped_column(
        String(20), default="locked", nullable=False
    )
    practice_status: Mapped[str] = mapped_column(
        String(20), default="locked", nullable=False
    )

    learn_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    learn_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    teaching_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    teaching_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    practice_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    practice_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    teaching_conversation_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    practice_conversation_id: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lesson_id",
            name="uq_user_lesson_stage_progress",
        ),
    )
