from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import (
    ENRICHMENT_STATUS_PATTERN,
    LANGUAGE_CODE_PATTERN,
    LEVEL_PATTERN,
)

class WordCreate(BaseModel):
    word: str = Field(
        min_length=1,
        max_length=255,
    )

    translation: str = Field(
        min_length=1,
        max_length=255,
    )


class WordFromVocabularyCreate(BaseModel):
    vocabulary_form_id: int = Field(
        ge=1,
    )


class WordResponse(BaseModel):
    id: int
    word: str
    translation: str
    learned: bool
    user_id: int
    learning_profile_id: int

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Learning Path
# =========================================================

class LearningPathLessonResponse(BaseModel):
    id: int
    language: str
    level: str
    unit_number: int
    lesson_order: int
    topic_key: str
    is_test: bool
    passing_score: float

    status: str
    completed: bool
    best_score: float
    attempts: int


class LearningPathResponse(BaseModel):
    language: str
    level: str
    progress: float
    completed_lessons: int
    total_lessons: int
    next_level: str | None
    lessons: list[LearningPathLessonResponse]


# =========================================================
# Complete Lesson
# =========================================================

class CompleteLessonRequest(BaseModel):
    score: float = Field(
        default=100.0,
        ge=0,
        le=100,
    )


class CompleteLessonResponse(BaseModel):
    message: str
    lesson_id: int
    completed: bool
    score: float
    level_upgraded: bool
    old_level: str
    new_level: str
    new_progress: float


# =========================================================
# Vocabulary Entry
# =========================================================

