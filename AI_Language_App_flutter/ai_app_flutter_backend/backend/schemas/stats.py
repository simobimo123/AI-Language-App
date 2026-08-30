from pydantic import BaseModel


class HomeStatsResponse(BaseModel):
    streak_days: int
    learned_words: int
    conversations: int
    learning_progress: float
    completed_lessons: int
    total_lessons: int