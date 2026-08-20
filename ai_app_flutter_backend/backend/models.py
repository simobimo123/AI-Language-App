from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    pass


# =========================================================
# User
# =========================================================

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

    # لغة المستخدم الأم
    native_language: Mapped[str] = mapped_column(
        String(10),
        default="ar",
        nullable=False
    )

    # لغة التعلم الحالية
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


# =========================================================
# Learning Profile
# =========================================================

class LearningProfile(Base):
    __tablename__ = "learning_profiles"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # رمز اللغة مثل:
    # en
    # fr
    # es
    # de
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    # المستوى الحالي
    level: Mapped[str] = mapped_column(
        String(2),
        default="A1",
        nullable=False
    )

    # التقدم من 0 إلى 100
    progress: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
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
            "language",
            name="uq_learning_profile_user_language"
        ),
    )


# =========================================================
# Word
# =========================================================

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

    # المستخدم صاحب الكلمة
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # اللغة التي تنتمي إليها هذه الكلمة
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "learning_profiles.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )