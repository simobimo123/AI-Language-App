from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LessonContent(Base):
    __tablename__ = "lesson_contents"

    id: Mapped[int] = mapped_column(primary_key=True)

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey(
            "course_lessons.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="DRAFT",
        nullable=False,
        index=True,
    )

    content: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    instruction_language: Mapped[str] = mapped_column(
        String(10),
        default="ar",
        nullable=False,
    )

    generator_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    generation_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "lesson_id",
            "instruction_language",
            name="uq_lesson_content_lesson_instruction_language",
        ),
    )
