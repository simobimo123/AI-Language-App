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
        String(10),
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

class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    lemma: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    word: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    part_of_speech: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )

    pronunciation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    frequency_rank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

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
# Vocabulary Relation
# =========================================================

class VocabularyRelation(Base):
    __tablename__ = "vocabulary_relations"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    source_entry_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_entries.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    target_entry_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_entries.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    relation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
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

    __table_args__ = (
        UniqueConstraint(
            "source_entry_id",
            "target_entry_id",
            "relation_type",
            name="uq_vocabulary_relation"
        ),
    )


# =========================================================
# Vocabulary Form
# =========================================================

class VocabularyForm(Base):
    __tablename__ = "vocabulary_forms"

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

    form: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    normalized_form: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    grammatical_features: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

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
            "vocabulary_entry_id",
            "form",
            name="uq_vocabulary_form_entry_form"
        ),
    )


# =========================================================
# Vocabulary Sense
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

    # Legacy fields.
    #
    # These remain temporarily for compatibility with
    # existing development data.
    #
    # New localized data should use
    # VocabularySenseLocalization.

    meaning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # =====================================================
    # Current / selected CEFR level
    # =====================================================
    #
    # This is the CEFR level currently used by the
    # application.
    #
    # Detailed assessments are stored separately in
    # VocabularyCEFRAssessment.
    #
    cefr_level: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True
    )

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
# Vocabulary CEFR Assessment
# =========================================================
#
# Stores every CEFR assessment made for a sense.
#
# One sense can have multiple assessments:
#
# dataset -> A1 -> 0.95
# ai      -> A2 -> 0.72
# manual  -> A1 -> 1.00
#
# VocabularySense.cefr_level remains the currently
# selected / accepted level.
# =========================================================

class VocabularyCEFRAssessment(Base):
    __tablename__ = "vocabulary_cefr_assessments"

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

    cefr_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    source_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
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
            "vocabulary_sense_id",
            "cefr_level",
            "source",
            "source_version",
            name="uq_vocabulary_cefr_assessment"
        ),
    )


# =========================================================
# Vocabulary Sense Localization
# =========================================================

class VocabularySenseLocalization(Base):
    __tablename__ = "vocabulary_sense_localizations"

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

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    meaning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    source_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
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
            "vocabulary_sense_id",
            "language",
            name="uq_vocabulary_sense_localization"
        ),
    )


# =========================================================
# Vocabulary Translation
# =========================================================

class VocabularyTranslation(Base):
    __tablename__ = "vocabulary_translations"

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

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )

    translation: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
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
            "vocabulary_sense_id",
            "language",
            "translation",
            name="uq_vocabulary_translation"
        ),
    )


# =========================================================
# Vocabulary Example
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

    level: Mapped[str | None] = mapped_column(
        String(10),
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
# Vocabulary Example Translation
# =========================================================

class VocabularyExampleTranslation(Base):
    __tablename__ = "vocabulary_example_translations"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_example_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vocabulary_examples.id",
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

    translation: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
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
            "vocabulary_example_id",
            "language",
            "translation",
            name="uq_vocabulary_example_translation"
        ),
    )


# =========================================================
# Vocabulary Media
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
        String(10),
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
        String(10),
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
# User Word
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