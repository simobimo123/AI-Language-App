from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LessonTarget(Base):
    """Canonical learning objective used by the active lesson stages."""

    __tablename__ = "lesson_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_key: Mapped[str] = mapped_column(String(100), nullable=False)
    target_order: Mapped[int] = mapped_column(Integer, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cefr_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("lesson_id", "target_key", name="uq_lesson_target_key"),
        UniqueConstraint("lesson_id", "target_order", name="uq_lesson_target_order"),
    )


class LessonTargetPattern(Base):
    """Accepted/expected linguistic patterns for one target."""

    __tablename__ = "lesson_target_patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(30), default="expected", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("target_id", "pattern", name="uq_lesson_target_pattern"),
    )


class LessonPracticeScenario(Base):
    """Natural contexts available to the practice stage."""

    __tablename__ = "lesson_practice_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("course_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_key: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("lesson_id", "scenario_key", name="uq_lesson_practice_scenario_key"),
    )


class UserLessonTargetProgress(Base):
    """Per-target evidence collected independently in teaching and practice."""

    __tablename__ = "user_lesson_target_progress"

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
    target_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    teaching_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    practice_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    teaching_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    practice_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    teaching_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    practice_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mastery_confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    last_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", "target_id", name="uq_user_lesson_target_progress"),
    )
