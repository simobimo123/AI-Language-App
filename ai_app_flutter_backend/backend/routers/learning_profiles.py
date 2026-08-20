from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schemas import (
    LearningProfileCreate,
    LearningProfileUpdate,
    LearningProfileResponse,
)
from models import LearningProfile, User
from database import get_db
from routers.auth import get_current_user


router = APIRouter(
    prefix="/learning",
    tags=["Learning"]
)


# =========================================================
# Get all learning profiles
# =========================================================

@router.get(
    "/profiles",
    response_model=list[LearningProfileResponse]
)
def get_learning_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profiles = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id
    ).all()

    return profiles


# =========================================================
# Get current learning profile
# =========================================================

@router.get(
    "/current",
    response_model=LearningProfileResponse
)
def get_current_learning_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == current_user.learning_language
    ).first()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Current learning profile not found"
        )

    return profile


# =========================================================
# Add a learning language
# =========================================================

@router.post(
    "/profiles",
    response_model=LearningProfileResponse
)
def create_learning_profile(
    profile_data: LearningProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # لا يمكن تعلم اللغة الأم
    if profile_data.language == current_user.native_language:
        raise HTTPException(
            status_code=400,
            detail="You cannot learn your native language"
        )

    existing_profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == profile_data.language
    ).first()

    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="Learning profile already exists"
        )

    new_profile = LearningProfile(
        user_id=current_user.id,
        language=profile_data.language,
        level=profile_data.level,
        progress=0.0
    )

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return new_profile


# =========================================================
# Update learning profile
# =========================================================

@router.put(
    "/profiles/{language}",
    response_model=LearningProfileResponse
)
def update_learning_profile(
    language: str,
    profile_data: LearningProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == language
    ).first()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learning profile not found"
        )

    profile.level = profile_data.level
    profile.progress = profile_data.progress

    db.commit()
    db.refresh(profile)

    return profile


# =========================================================
# Switch current learning language
# =========================================================

@router.put("/current/{language}")
def switch_learning_language(
    language: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == language
    ).first()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Learning profile not found"
        )

    current_user.learning_language = language

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Learning language switched successfully",
        "learning_language": current_user.learning_language,
        "level": profile.level,
        "progress": profile.progress
    }
