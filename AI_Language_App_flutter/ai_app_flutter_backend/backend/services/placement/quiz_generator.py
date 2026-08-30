from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import PlacementQuizQuestion, PlacementVocabulary
from services.placement.config import (
    QUIZ_QUESTIONS_PER_TEST,
    WORDS_PER_LEVEL,
)


def get_random_level_words(
    language: str,
    level: str,
    db: Session,
) -> list[PlacementVocabulary]:

    statement = (
        select(
            PlacementVocabulary
        )
        .where(
            PlacementVocabulary.language
            == language,
            PlacementVocabulary.level
            == level,
            PlacementVocabulary.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            WORDS_PER_LEVEL
        )
    )

    words = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(words) < WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active vocabulary "
                f"for {language}/{level}. "
                f"Required: {WORDS_PER_LEVEL}, "
                f"available: {len(words)}."
            ),
        )

    return words


def get_random_quiz_questions(
    language: str,
    level: str,
    db: Session,
) -> list[PlacementQuizQuestion]:

    statement = (
        select(
            PlacementQuizQuestion
        )
        .where(
            PlacementQuizQuestion.language
            == language,
            PlacementQuizQuestion.level
            == level,
            PlacementQuizQuestion.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            QUIZ_QUESTIONS_PER_TEST
        )
    )

    questions = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(questions) < QUIZ_QUESTIONS_PER_TEST:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active quiz questions "
                f"for {language}/{level}. "
                f"Required: "
                f"{QUIZ_QUESTIONS_PER_TEST}, "
                f"available: {len(questions)}."
            ),
        )

    return questions
