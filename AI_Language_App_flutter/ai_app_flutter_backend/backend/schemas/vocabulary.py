from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import (
    ENRICHMENT_STATUS_PATTERN,
    LANGUAGE_CODE_PATTERN,
    LEVEL_PATTERN,
)

class VocabularyEntryCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    lemma: str = Field(
        min_length=1,
        max_length=255,
    )

    word: str | None = Field(
        default=None,
        max_length=255,
    )

    normalized_lemma: str | None = Field(
        default=None,
        max_length=255,
    )

    part_of_speech: str | None = Field(
        default=None,
        max_length=50,
    )

    pronunciation: str | None = Field(
        default=None,
        max_length=255,
    )

    frequency_rank: int | None = Field(
        default=None,
        ge=0,
    )

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )

    enrichment_status: str = Field(
        default="partial",
        pattern=ENRICHMENT_STATUS_PATTERN,
    )


class VocabularyEntryResponse(BaseModel):
    id: int
    language: str
    lemma: str
    normalized_lemma: str | None
    word: str | None
    part_of_speech: str | None
    pronunciation: str | None
    frequency_rank: int | None
    source: str | None
    source_version: str | None

    enrichment_status: str
    last_enriched_at: datetime | None
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Relation
# =========================================================

class VocabularyRelationCreate(BaseModel):
    target_entry_id: int = Field(
        ge=1,
    )

    relation_type: str = Field(
        min_length=1,
        max_length=50,
    )

    source_sense_id: int | None = Field(
        default=None,
        ge=1,
    )

    target_sense_id: int | None = Field(
        default=None,
        ge=1,
    )

    is_bidirectional: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )


class VocabularyRelationResponse(BaseModel):
    id: int
    source_entry_id: int
    target_entry_id: int

    source_sense_id: int | None
    target_sense_id: int | None

    relation_type: str
    language: str
    is_bidirectional: bool
    is_active: bool

    source: str | None
    source_version: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Form
# =========================================================

class VocabularyFormCreate(BaseModel):
    form: str = Field(
        min_length=1,
        max_length=255,
    )

    normalized_form: str | None = Field(
        default=None,
        max_length=255,
    )

    grammatical_features: dict | None = None

    form_type: str | None = Field(
        default=None,
        max_length=50,
    )

    is_lemma: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )


class VocabularyFormResponse(BaseModel):
    id: int
    vocabulary_entry_id: int
    form: str
    normalized_form: str
    grammatical_features: dict | None

    form_type: str | None
    is_lemma: bool

    source: str | None
    source_version: str | None
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Sense
# =========================================================

class VocabularySenseCreate(BaseModel):
    cefr_level: str | None = Field(
        default=None,
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )

    frequency_rank: int | None = Field(
        default=None,
        ge=0,
    )

    enrichment_status: str = Field(
        default="partial",
        pattern=ENRICHMENT_STATUS_PATTERN,
    )

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class VocabularySenseResponse(BaseModel):
    id: int
    vocabulary_entry_id: int

    # Legacy compatibility.
    meaning: str | None
    definition: str | None

    cefr_level: str | None
    frequency_rank: int | None

    enrichment_status: str
    quality_score: float | None
    last_enriched_at: datetime | None

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary CEFR Assessment
# =========================================================

class VocabularyCEFRAssessmentCreate(BaseModel):
    cefr_level: str = Field(
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )

    source: str = Field(
        min_length=1,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )

    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    is_selected: bool = False


class VocabularyCEFRAssessmentResponse(BaseModel):
    id: int
    vocabulary_sense_id: int

    cefr_level: str
    source: str
    source_version: str | None
    confidence: float
    is_selected: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Sense Localization
# =========================================================

class VocabularySenseLocalizationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    meaning: str | None = None
    definition: str | None = None

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )

    enrichment_status: str = Field(
        default="partial",
        pattern=ENRICHMENT_STATUS_PATTERN,
    )

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    generated_by_ai: bool = False


class VocabularySenseLocalizationResponse(BaseModel):
    id: int
    vocabulary_sense_id: int

    language: str
    meaning: str | None
    definition: str | None

    source: str | None
    source_version: str | None

    enrichment_status: str
    quality_score: float | None
    generated_by_ai: bool
    last_enriched_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Translation
# =========================================================

class VocabularyTranslationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    translation: str = Field(
        min_length=1,
        max_length=1000,
    )

    translated_entry_id: int | None = Field(
        default=None,
        ge=1,
    )

    is_primary: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )

    generated_by_ai: bool = False

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class VocabularyTranslationResponse(BaseModel):
    id: int
    vocabulary_sense_id: int

    language: str
    translation: str

    translated_entry_id: int | None

    is_primary: bool

    source: str | None
    source_version: str | None

    generated_by_ai: bool
    quality_score: float | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Example
# =========================================================

class VocabularyExampleCreate(BaseModel):
    sentence: str = Field(
        min_length=1,
        max_length=5000,
    )

    level: str | None = Field(
        default=None,
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    generated_by_ai: bool = False

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class VocabularyExampleResponse(BaseModel):
    id: int
    vocabulary_sense_id: int

    sentence: str
    level: str | None

    source: str | None

    generated_by_ai: bool
    quality_score: float | None

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Example Translation
# =========================================================

class VocabularyExampleTranslationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    translation: str = Field(
        min_length=1,
        max_length=5000,
    )

    is_primary: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    source_version: str | None = Field(
        default=None,
        max_length=100,
    )

    generated_by_ai: bool = False

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class VocabularyExampleTranslationResponse(BaseModel):
    id: int
    vocabulary_example_id: int

    language: str
    translation: str

    is_primary: bool

    source: str | None
    source_version: str | None

    generated_by_ai: bool
    quality_score: float | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Vocabulary Media
# =========================================================

class VocabularyMediaCreate(BaseModel):
    media_type: str = Field(
        min_length=1,
        max_length=30,
    )

    url: str = Field(
        min_length=1,
        max_length=5000,
    )

    thumbnail_url: str | None = Field(
        default=None,
        max_length=5000,
    )

    alt_text: str | None = Field(
        default=None,
        max_length=1000,
    )

    source: str | None = Field(
        default=None,
        max_length=100,
    )

    generated_by_ai: bool = False


class VocabularyMediaResponse(BaseModel):
    id: int
    vocabulary_sense_id: int

    media_type: str
    url: str
    thumbnail_url: str | None
    alt_text: str | None

    source: str | None

    generated_by_ai: bool
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# User-localized Vocabulary Responses
# =========================================================

class VocabularyLocalizedExampleResponse(BaseModel):
    id: int
    sentence: str
    level: str | None

    translation_language: str
    translation: str | None


class VocabularyLocalizedSenseResponse(BaseModel):
    id: int
    vocabulary_entry_id: int

    cefr_level: str | None
    frequency_rank: int | None

    learning_language: str
    native_language: str

    learning_meaning: str | None
    learning_definition: str | None

    native_meaning: str | None
    native_definition: str | None

    native_translation: str | None

    enrichment_status: str
    quality_score: float | None

    examples: list[
        VocabularyLocalizedExampleResponse
    ]


class VocabularyLocalizedEntryResponse(BaseModel):
    id: int

    language: str

    lemma: str
    normalized_lemma: str | None
    word: str | None

    part_of_speech: str | None
    pronunciation: str | None
    frequency_rank: int | None

    source: str | None
    source_version: str | None

    learning_language: str
    native_language: str

    enrichment_status: str
    quality_score: float | None

    senses: list[
        VocabularyLocalizedSenseResponse
    ]


# =========================================================
# Placement Vocabulary
# =========================================================

