from datetime import datetime, date

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    Integer,
    UniqueConstraint,
    Date,
    Text,
    JSON,
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

    # Google account unique identifier.
    # This stores Google's "sub" value.
    google_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True
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


# =========================================================
# Learning Profile
# =========================================================

class LearningProfile(Base):
    __tablename__ = "learning_profiles"

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

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    level: Mapped[str] = mapped_column(
        String(2),
        default="A1",
        nullable=False,
        index=True
    )

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
# Vocabulary Entry
# =========================================================
#
# The main lexical item.
#
# Example:
#
# language = "en"
# lemma = "case"
# part_of_speech = "noun"
#
# The same word can have multiple meanings.
# Those meanings are stored in VocabularySense.
# =========================================================

class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # Language code:
    # en, ar, fr, es, de, tr, ja, ko, zh, ...
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    # Base dictionary form.
    # Example:
    # running -> run
    lemma: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # Optional displayed form.
    # Usually equal to lemma, but useful for inflected forms.
    word: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # noun, verb, adjective, adverb, ...
    part_of_speech: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )

    # IPA or another pronunciation representation.
    pronunciation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Optional numerical frequency rank.
    #
    # Lower rank can represent a more frequent word,
    # depending on the source.
    frequency_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    # Where this entry came from.
    #
    # Examples:
    # CEFR-J
    # UniversalCEFR
    # imported_dataset
    # manual
    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    # Dataset/source version.
    source_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
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
            "language",
            "lemma",
            "part_of_speech",
            name="uq_vocabulary_entry_language_lemma_pos"
        ),
    )


# =========================================================
# Vocabulary Sense
# =========================================================
#
# One word can have multiple meanings.
#
# Example:
#
# case
#   -> situation
#   -> legal matter
#   -> container
#
# Each meaning can have its own CEFR level.
# =========================================================

class VocabularySense(Base):
    __tablename__ = "vocabulary_senses"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_entry_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_entries.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Meaning written in a language understandable by the learner.
    meaning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Dictionary-style definition in the target language.
    definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Optional translation.
    #
    # This may depend on the user's native language, so it is
    # not necessarily globally unique.
    translation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # CEFR level for THIS meaning.
    #
    # A1, A2, B1, B2, C1, C2
    cefr_level: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True
    )

    # Optional frequency for this particular sense.
    frequency_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
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


# =========================================================
# Vocabulary Example
# =========================================================
#
# Examples are linked to a meaning, not only to a word.
#
# This allows:
#
# case -> "a situation"
# example:
# "This is a difficult case."
#
# case -> "a container"
# example:
# "Put the glasses in the case."
# =========================================================

class VocabularyExample(Base):
    __tablename__ = "vocabulary_examples"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_sense_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_senses.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    sentence: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    translation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Optional CEFR level for this example.
    level: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# Vocabulary Media
# =========================================================
#
# Media belongs to a specific sense.
#
# type can be:
#
# image
# audio
# video
# animation
#
# We store URLs/paths, not the binary files themselves.
# =========================================================

class VocabularyMedia(Base):
    __tablename__ = "vocabulary_media"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_sense_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_senses.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    media_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    alt_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# Legacy Placement Vocabulary
# =========================================================
#
# TEMPORARY COMPATIBILITY TABLE
#
# The current placement_test.py still uses this table.
#
# We will migrate the placement system to the new
# VocabularyEntry/VocabularySense structure later.
#
# Do NOT delete this table yet.
# =========================================================

class PlacementVocabulary(Base):
    __tablename__ = "placement_vocabulary"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    level: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True
    )

    word: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
            "word",
            name="uq_placement_vocabulary"
        ),
    )


# =========================================================
# Placement Quiz Question
# =========================================================
#
# This is the "real" confirmation test used after the user
# stops climbing levels in the quick vocabulary screening.
#
# Unlike PlacementVocabulary (single words, yes/no known),
# this holds grammar/comprehension multiple-choice questions
# for a specific language + level.
#
# `choices` is stored as a JSON array of strings, e.g.:
# ["is", "are", "am", "be"]
#
# `correct_index` is the 0-based index of the right answer
# inside `choices`.
# =========================================================

class PlacementQuizQuestion(Base):
    __tablename__ = "placement_quiz_questions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    level: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    choices: Mapped[list] = mapped_column(
        JSON,
        nullable=False
    )

    correct_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
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
            "question",
            name="uq_placement_quiz_question"
        ),
    )


# =========================================================
# Course Lesson
# =========================================================

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
        String(2),
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
# User Word
# =========================================================
#
# This is the user's personal vocabulary.
#
# It remains separate from the global vocabulary database.
#
# A user can save a word/meaning from the global vocabulary
# or create their own word.
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# AI Usage
# =========================================================

class AIUsage(Base):
    __tablename__ = "ai_usage"

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

    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    request_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
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
            "usage_date",
            name="uq_ai_usage_user_date"
        ),
    )


# =========================================================
# AI Conversation Message
# =========================================================

class AIConversationMessage(Base):
    __tablename__ = "ai_conversation_messages"

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

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )