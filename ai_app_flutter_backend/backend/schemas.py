from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================================================
# Constants
# =========================================================

LEVEL_PATTERN = (
    r"^(PRE_A1|A1|A2|B1|B2|C1|C2)$"
)

LANGUAGE_CODE_PATTERN = (
    r"^(ar|de|en|es|fa|fr|hi|id|it|ja|ko|nl|pl|pt|ru|th|tr|uk|vi|zh)$"
)

ENRICHMENT_STATUS_PATTERN = (
    r"^(partial|complete|needs_review)$"
)


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
        pattern=LANGUAGE_CODE_PATTERN,
    )

    learning_language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
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
        pattern=LANGUAGE_CODE_PATTERN,
    )

    learning_language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    native_language: str
    learning_language: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Learning Profile
# =========================================================

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


# =========================================================
# Placement Vocabulary Evaluation
# =========================================================

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


# =========================================================
# Placement Quiz
# =========================================================

class PlacementQuizQuestionOut(BaseModel):
    id: int
    question: str
    choices: list[str]

    question_type: str = "multiple_choice"
    explanation: str | None = None


class PlacementQuizResponse(BaseModel):
    language: str
    level: str

    questions: list[
        PlacementQuizQuestionOut
    ]


class PlacementQuizAnswer(BaseModel):
    question_id: int

    selected_index: int = Field(
        ge=0,
    )


class PlacementQuizEvaluationRequest(BaseModel):
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

    answers: list[PlacementQuizAnswer] = Field(
        min_length=1,
        max_length=10,
    )


class PlacementQuizEvaluationResponse(BaseModel):
    language: str
    level: str

    total_questions: int
    correct_answers: int
    percentage: float

    passed: bool
    final_level: str


# =========================================================
# Placement Attempt
# =========================================================

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
    confirmation_percentage: float | None

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


class PlacementAttemptQuestionResponse(BaseModel):
    id: int
    attempt_id: int
    placement_question_id: int
    position: int

    selected_index: int | None
    is_correct: bool | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Placement Finalize
# =========================================================

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


# =========================================================
# Vocabulary Enrichment
# =========================================================

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