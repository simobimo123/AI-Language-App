from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .common import LANGUAGE_CODE_PATTERN, LEVEL_PATTERN


class PlacementWord(BaseModel):
    id: int
    word: str
    level: str

    vocabulary_sense_id: int | None = None
    vocabulary_form_id: int | None = None


class PlacementWordsResponse(BaseModel):
    language: str
    level: str
    words: list[PlacementWord]


class PlacementWordEvaluationRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    level: str = Field(
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )

    presented_word_ids: list[int] = Field(
        min_length=1,
        max_length=20,
    )

    selected_word_ids: list[int] = Field(
        default_factory=list,
        max_length=20,
    )


class PlacementWordEvaluationResponse(BaseModel):
    language: str
    level: str

    total_words: int
    known_words: int
    percentage: float

    passed: bool
    next_level: str | None

    preliminary_level: str


class PlacementAttemptCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )


class PlacementAttemptResponse(BaseModel):
    id: int
    user_id: int
    language: str

    stage: str

    preliminary_level: str | None
    final_level: str | None

    vocabulary_percentage: float | None

    status: str

    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True,
    )


class PlacementAttemptWordResponse(BaseModel):
    id: int
    attempt_id: int
    placement_vocabulary_id: int
    position: int
    was_selected: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


class PlacementFinalizeRequest(BaseModel):
    attempt_id: int = Field(
        ge=1,
    )


class PlacementFinalizeResponse(BaseModel):
    message: str
    attempt_id: int
    language: str
    level: str
    progress: float
