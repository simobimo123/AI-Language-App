from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import LearningProfile, PlacementAttempt, User


def get_attempt_or_404(
    attempt_id: int,
    current_user: User,
    db: Session,
) -> PlacementAttempt:

    attempt = (
        db.query(PlacementAttempt)
        .filter(
            PlacementAttempt.id == attempt_id,
            PlacementAttempt.user_id
            == current_user.id,
        )
        .first()
    )

    if attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Placement attempt not found.",
        )

    return attempt


def get_current_learning_profile(
    language: str,
    current_user: User,
    db: Session,
) -> LearningProfile | None:

    return (
        db.query(
            LearningProfile
        )
        .filter(
            LearningProfile.user_id
            == current_user.id,
            LearningProfile.language
            == language,
        )
        .first()
    )
