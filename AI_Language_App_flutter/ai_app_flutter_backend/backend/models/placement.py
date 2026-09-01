from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PlacementVocabulary(Base):
    __tablename__ = "placement_vocabulary"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    word: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    vocabulary_sense_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_senses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    vocabulary_form_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_forms.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "language",
            "level",
            "word",
            name="uq_placement_vocabulary",
        ),
        Index(
            "ix_placement_vocabulary_sense_level",
            "vocabulary_sense_id",
            "level",
        ),
    )


class PlacementAttempt(Base):
    __tablename__ = "placement_attempts"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    stage: Mapped[str] = mapped_column(
        String(30),
        default="vocabulary",
        nullable=False,
        index=True,
    )

    preliminary_level: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )

    final_level: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )

    vocabulary_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class PlacementAttemptWord(Base):
    __tablename__ = "placement_attempt_words"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    attempt_id: Mapped[int] = mapped_column(
        ForeignKey(
            "placement_attempts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    placement_vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey(
            "placement_vocabulary.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    was_selected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "placement_vocabulary_id",
            name="uq_placement_attempt_word",
        ),
        UniqueConstraint(
            "attempt_id",
            "position",
            name="uq_placement_attempt_word_position",
        ),
    )
