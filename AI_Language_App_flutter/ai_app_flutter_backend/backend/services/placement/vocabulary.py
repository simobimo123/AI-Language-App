from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import PlacementVocabulary
from services.placement.config import (
    VOCABULARY_BANK_SIZE,
    WORDS_PER_LEVEL,
)


def get_random_level_words(
    language: str,
    level: str,
    db: Session,
) -> list[PlacementVocabulary]:
    """
    Return exactly 20 random words from a 100-word level bank.

    The database is expected to contain at least
    VOCABULARY_BANK_SIZE active words for every language/level.
    """
    bank_count = db.execute(
        select(func.count(PlacementVocabulary.id)).where(
            PlacementVocabulary.language == language,
            PlacementVocabulary.level == level,
            PlacementVocabulary.is_active.is_(True),
        )
    ).scalar_one()

    if bank_count < VOCABULARY_BANK_SIZE:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active vocabulary for {language}/{level}. "
                f"A complete placement bank requires {VOCABULARY_BANK_SIZE} words, "
                f"available: {bank_count}."
            ),
        )

    statement = (
        select(PlacementVocabulary)
        .where(
            PlacementVocabulary.language == language,
            PlacementVocabulary.level == level,
            PlacementVocabulary.is_active.is_(True),
        )
        .order_by(func.random())
        .limit(WORDS_PER_LEVEL)
    )

    words = db.execute(statement).scalars().all()

    if len(words) != WORDS_PER_LEVEL:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not generate exactly {WORDS_PER_LEVEL} random words "
                f"for {language}/{level}."
            ),
        )

    return words
