from pydantic import BaseModel, Field


class GenerateLessonContentRequest(BaseModel):
    lesson_id: int = Field(gt=0)
    instruction_language: str = Field(default="ar", min_length=2, max_length=10)
    force_regenerate: bool = False


class LessonContentResponse(BaseModel):
    id: int
    lesson_id: int
    status: str
    instruction_language: str
    generator_model: str | None
    version: int
    content: dict

    model_config = {"from_attributes": True}
