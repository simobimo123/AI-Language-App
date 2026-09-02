from pydantic import BaseModel, Field


class LessonAssessmentOption(BaseModel):
    id: str
    text: str


class LessonAssessmentQuestion(BaseModel):
    id: str
    order: int
    type: str
    question: str
    options: list[LessonAssessmentOption]


class LessonAssessmentResponse(BaseModel):
    lesson_id: int
    passing_score: float
    question_count: int
    questions: list[LessonAssessmentQuestion]


class LessonAssessmentAnswer(BaseModel):
    question_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class LessonAssessmentSubmitRequest(BaseModel):
    answers: list[LessonAssessmentAnswer] = Field(default_factory=list)


class LessonAssessmentResult(BaseModel):
    lesson_id: int
    score: float
    passed: bool
    correct_count: int
    total_questions: int
    attempts: int
    best_score: float
    completed: bool
    level_upgraded: bool
    old_level: str
    new_level: str
    new_progress: float
