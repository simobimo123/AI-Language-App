from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import (
    ENRICHMENT_STATUS_PATTERN,
    LANGUAGE_CODE_PATTERN,
    LEVEL_PATTERN,
)

class VocabularyEnrichmentRequest(BaseModel):
    vocabulary_entry_id: int = Field(
        ge=1,
    )

    sense_id: int | None = Field(
        default=None,
        ge=1,
    )

    target_languages: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    generate_missing_only: bool = True


class VocabularyEnrichmentFieldStatus(BaseModel):
    field_name: str
    language: str | None = None

    present: bool

    source: str | None = None
    generated_by_ai: bool = False


class VocabularyEnrichmentResponse(BaseModel):
    vocabulary_entry_id: int
    sense_id: int | None

    fields: list[
        VocabularyEnrichmentFieldStatus
    ]

    completed: bool
    missing_fields: list[str]


# =========================================================
# AI Usage
# =========================================================

class AIUsageResponse(BaseModel):
    id: int
    user_id: int

    usage_date: date

    request_count: int
    api_call_count: int

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    estimated_cost: float

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# AI Conversation
# =========================================================

class AIConversationMessageResponse(BaseModel):
    id: int
    user_id: int

    conversation_id: str | None

    role: str
    content: str

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )