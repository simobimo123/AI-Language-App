from pydantic import BaseModel, ConfigDict, Field


class SentenceCreate(BaseModel):
    sentence: str = Field(min_length=1, max_length=255)
    translation: str = Field(min_length=1, max_length=255)


class SentenceResponse(BaseModel):
    id: int
    sentence: str
    translation: str
    learned: bool
    user_id: int
    learning_profile_id: int

    model_config = ConfigDict(from_attributes=True)
