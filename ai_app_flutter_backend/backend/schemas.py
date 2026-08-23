from pydantic import BaseModel, EmailStr, Field


LEVEL_PATTERN = r"^(A1|A2|B1|B2|C1|C2)$"


# =========================================================
# User
# =========================================================

class UserCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )

    native_language: str = Field(
        default="ar",
        min_length=2,
        max_length=10
    )

    learning_language: str = Field(
        default="en",
        min_length=2,
        max_length=10
    )

    learning_level: str = Field(
        default="A1",
        min_length=2,
        max_length=2,
        pattern=LEVEL_PATTERN
    )


class UserLogin(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128
    )


# =========================================================
# Google Login
# =========================================================

class GoogleLogin(BaseModel):
    id_token: str = Field(
        min_length=1
    )


class UserUpdate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    native_language: str = Field(
        min_length=2,
        max_length=10
    )

    learning_language: str = Field(
        min_length=2,
        max_length=10
    )


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    native_language: str
    learning_language: str

    class Config:
        from_attributes = True


# =========================================================
# Learning Profile
# =========================================================

class LearningProfileCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10
    )

    level: str = Field(
        default="A1",
        min_length=2,
        max_length=2,
        pattern=LEVEL_PATTERN
    )


class LearningProfileUpdate(BaseModel):
    level: str = Field(
        min_length=2,
        max_length=2,
        pattern=LEVEL_PATTERN
    )

    progress: float = Field(
        ge=0,
        le=100
    )


class LearningProfileResponse(BaseModel):
    id: int
    language: str
    level: str
    progress: float

    class Config:
        from_attributes = True


# =========================================================
# Word
# =========================================================

class WordCreate(BaseModel):
    word: str = Field(
        min_length=1,
        max_length=255
    )

    translation: str = Field(
        min_length=1,
        max_length=255
    )


class WordResponse(BaseModel):
    id: int
    word: str
    translation: str
    learned: bool
    user_id: int
    learning_profile_id: int

    class Config:
        from_attributes = True


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
        le=100
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
