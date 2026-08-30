from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import (
    ENRICHMENT_STATUS_PATTERN,
    LANGUAGE_CODE_PATTERN,
    LEVEL_PATTERN,
)

class LearningProfileCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    level: str = Field(
        default="A1",
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )


class LearningProfileUpdate(BaseModel):
    level: str = Field(
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )

    progress: float = Field(
        ge=0,
        le=100,
    )


class LearningProfileResponse(BaseModel):
    id: int
    language: str
    level: str
    progress: float

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Word
# =========================================================

