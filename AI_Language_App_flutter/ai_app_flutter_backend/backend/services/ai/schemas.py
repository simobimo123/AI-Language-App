from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        max_length=800,
    )

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


# =========================================================
# Classification
# =========================================================

class AIRequestClassification(BaseModel):

    decision: Literal[
        "ALLOW",
        "LIMIT",
        "BLOCK",
    ]

    reason: str

    needs_vocabulary_enrichment: bool = False

    vocabulary_word: str | None = None

    vocabulary_request_type: Literal[
        "meaning",
        "translation",
        "definition",
        "example",
        "pronunciation",
        "general",
        "none",
    ] = "none"


# =========================================================
# AI vocabulary schemas
# =========================================================

class AIVocabularyForm(BaseModel):

    form: str = Field(
        min_length=1,
        max_length=255,
    )

    form_type: str | None = Field(
        default=None,
        max_length=50,
    )

    is_lemma: bool = False

    grammatical_features: dict | None = None


class AIVocabularyRelation(BaseModel):

    word: str = Field(
        min_length=1,
        max_length=255,
    )

    relation_type: Literal[
        "synonym",
        "antonym",
        "related",
        "derived",
        "hypernym",
        "hyponym",
        "holonym",
        "meronym",
        "coordinate_term",
        "see_also",
    ]

    part_of_speech: str | None = None


class AIExampleTranslation(BaseModel):

    language: str = Field(
        min_length=2,
        max_length=10,
    )

    translation: str = Field(
        min_length=1,
        max_length=5000,
    )


class AIVocabularyEnrichment(BaseModel):

    word: str

    language: str

    part_of_speech: str | None = None

    pronunciation: str | None = None

    cefr_level: str | None = None

    cefr_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    meaning: str | None = None

    definition: str | None = None

    native_translation: str | None = None

    native_definition: str | None = None

    forms: list[
        AIVocabularyForm
    ] = Field(
        default_factory=list
    )

    relations: list[
        AIVocabularyRelation
    ] = Field(
        default_factory=list
    )

    example_sentence: str | None = Field(
        default=None,
        max_length=5000,
    )

    example_translations: list[
        AIExampleTranslation
    ] = Field(
        default_factory=list
    )



# =========================================================
# Enrichment result
# =========================================================

class VocabularyEnrichmentResult(BaseModel):

    word: str

    entry_id: int

    sense_id: int

    generated: bool

    missing_before: list[str]

    completed_fields: list[str]

    remaining_fields: list[str]

    database_context: str
