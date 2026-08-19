from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    native_language: Mapped[str] = mapped_column(
        String(10),
        default="ar",
        nullable=False
    )

    learning_language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    word: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    translation: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    learned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
