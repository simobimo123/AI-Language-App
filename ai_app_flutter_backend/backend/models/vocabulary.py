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

    normalized_lemma: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    # -----------------------------------------------------
    # Enrichment state
    # -----------------------------------------------------

    enrichment_status: Mapped[str] = mapped_column(
        String(30),
        default="partial",
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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
        Index(
            "ix_vocabulary_entry_language_normalized_lemma",
            "language",
            "normalized_lemma",
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

    source_sense_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_senses.id",
            ondelete="CASCADE"
        ),
        nullable=True,
        index=True
    )

    target_sense_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_senses.id",
            ondelete="CASCADE"
        ),
        nullable=True,
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

    is_bidirectional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
        Index(
            "ix_vocabulary_relation_source_sense",
            "source_sense_id",
        ),
        Index(
            "ix_vocabulary_relation_target_sense",
            "target_sense_id",
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

    form_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True
    )

    is_lemma: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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
            "vocabulary_entry_id",
            "form",
            name="uq_vocabulary_form_entry_form"
        ),
        Index(
            "ix_vocabulary_form_entry_normalized_form",
            "vocabulary_entry_id",
            "normalized_form",
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

    # Legacy compatibility fields.
    meaning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    definition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

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

    enrichment_status: Mapped[str] = mapped_column(
        String(30),
        default="partial",
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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
        Index(
            "ix_vocabulary_sense_entry_level",
            "vocabulary_entry_id",
            "cefr_level",
        ),
    )


# =========================================================
# Vocabulary CEFR Assessment
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

    is_selected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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
            "vocabulary_sense_id",
            "cefr_level",
            "source",
            "source_version",
            name="uq_vocabulary_cefr_assessment"
        ),
        Index(
            "ix_vocabulary_cefr_assessment_sense_confidence",
            "vocabulary_sense_id",
            "confidence",
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

    enrichment_status: Mapped[str] = mapped_column(
        String(30),
        default="partial",
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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

    translated_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "vocabulary_entries.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    source_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
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

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
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

    __table_args__ = (
        Index(
            "ix_vocabulary_example_sense_level",
            "vocabulary_sense_id",
            "level",
        ),
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
        nullable=False,
        index=True
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    source_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
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

    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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

    __table_args__ = (
        UniqueConstraint(
            "vocabulary_sense_id",
            "media_type",
            "url",
            name="uq_vocabulary_media"
        ),
    )


# =========================================================
# Placement Vocabulary
# =========================================================

