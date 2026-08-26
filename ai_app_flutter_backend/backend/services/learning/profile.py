from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import LearningProfile, User


def get_current_learning_profile(
    db: Session,
    current_user: User,
    not_found_detail: str = "Current learning profile not found",
) -> LearningProfile:
    """Return the profile for the language the user is currently learning."""
    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == current_user.learning_language,
        )
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=not_found_detail,
        )

    return profile


