from pydantic import BaseModel, EmailStr, Field


# =========================================================
# Constants
# =========================================================

LEVEL_PATTERN = r"^(PRE_A1|A1|A2|B1|B2|C1|C2)$"


# =========================================================
# User
# =========================================================

class UserCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    native_language: str = Field(
        default="ar",
        min_length=2,
        max_length=10,
    )

    learning_language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
    )

    learning_level: str = Field(
        default="A1",
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )


class UserLogin(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


# =========================================================
# Google Login
# =========================================================

class GoogleLogin(BaseModel):
    id_token: str = Field(
        min_length=1,
    )


class UserUpdate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    native_language: str = Field(
        min_length=2,
        max_length=10,
    )

    learning_language: str = Field(
        min_length=2,
        max_length=10,
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
        max_length=10,
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

    class Config:
        from_attributes = True


# =========================================================
# Word
# =========================================================

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

class VocabularyEntryCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    lemma: str = Field(
        min_length=1,
        max_length=255,
    )

    word: str | None = Field(
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


class VocabularyEntryResponse(BaseModel):
    id: int
    language: str
    lemma: str
    word: str | None
    part_of_speech: str | None
    pronunciation: str | None
    frequency_rank: int | None
    source: str | None
    source_version: str | None

    class Config:
        from_attributes = True


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


class VocabularyRelationResponse(BaseModel):
    id: int
    source_entry_id: int
    target_entry_id: int
    relation_type: str
    language: str
    is_active: bool

    class Config:
        from_attributes = True


# =========================================================
# Vocabulary Form
# =========================================================

class VocabularyFormCreate(BaseModel):
    form: str = Field(
        min_length=1,
        max_length=255,
    )

    grammatical_features: dict | None = None

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
    source: str | None
    source_version: str | None
    is_active: bool

    class Config:
        from_attributes = True


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


class VocabularySenseResponse(BaseModel):
    id: int
    vocabulary_entry_id: int
    cefr_level: str | None
    frequency_rank: int | None
    is_active: bool

    class Config:
        from_attributes = True


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


class VocabularyCEFRAssessmentResponse(BaseModel):
    id: int
    vocabulary_sense_id: int
    cefr_level: str
    source: str
    source_version: str | None
    confidence: float

    class Config:
        from_attributes = True


# =========================================================
# Vocabulary Sense Localization
# =========================================================

class VocabularySenseLocalizationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
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


class VocabularySenseLocalizationResponse(BaseModel):
    id: int
    vocabulary_sense_id: int
    language: str
    meaning: str | None
    definition: str | None
    source: str | None
    source_version: str | None

    class Config:
        from_attributes = True


# =========================================================
# Vocabulary Translation
# =========================================================

class VocabularyTranslationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    translation: str = Field(
        min_length=1,
    )

    is_primary: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )


class VocabularyTranslationResponse(BaseModel):
    id: int
    vocabulary_sense_id: int
    language: str
    translation: str
    is_primary: bool
    source: str | None

    class Config:
        from_attributes = True


# =========================================================
# Vocabulary Example
# =========================================================

class VocabularyExampleCreate(BaseModel):
    sentence: str = Field(
        min_length=1,
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


class VocabularyExampleResponse(BaseModel):
    id: int
    vocabulary_sense_id: int
    sentence: str
    level: str | None
    source: str | None
    is_active: bool

    class Config:
        from_attributes = True


# =========================================================
# Vocabulary Example Translation
# =========================================================

class VocabularyExampleTranslationCreate(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    translation: str = Field(
        min_length=1,
    )

    is_primary: bool = False

    source: str | None = Field(
        default=None,
        max_length=100,
    )


class VocabularyExampleTranslationResponse(BaseModel):
    id: int
    vocabulary_example_id: int
    language: str
    translation: str
    is_primary: bool
    source: str | None

    class Config:
        from_attributes = True


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
    )

    thumbnail_url: str | None = None

    alt_text: str | None = None

    source: str | None = Field(
        default=None,
        max_length=100,
    )


class VocabularyMediaResponse(BaseModel):
    id: int
    vocabulary_sense_id: int
    media_type: str
    url: str
    thumbnail_url: str | None
    alt_text: str | None
    source: str | None
    is_active: bool

    class Config:
        from_attributes = True


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

    examples: list[VocabularyLocalizedExampleResponse]


class VocabularyLocalizedEntryResponse(BaseModel):
    id: int
    language: str
    lemma: str
    word: str | None
    part_of_speech: str | None
    pronunciation: str | None
    frequency_rank: int | None
    source: str | None
    source_version: str | None

    learning_language: str
    native_language: str

    senses: list[VocabularyLocalizedSenseResponse]
