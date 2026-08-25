from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from schemas import (
    LearningProfileCreate,
    LearningProfileUpdate,
    LearningProfileResponse,
)
from models import (
    LearningProfile,
    User,
)
from database import get_db
from routers.auth import get_current_user


router = APIRouter(
    prefix="/learning",
    tags=["Learning"],
)


# =========================================================
# Constants
# =========================================================

SUPPORTED_LANGUAGES = {
    "ar",
    "de",
    "en",
    "es",
    "fa",
    "fr",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "th",
    "tr",
    "uk",
    "vi",
    "zh",
}


SUPPORTED_LEVELS = {
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
}


# =========================================================
# Helpers
# =========================================================

def normalize_language(
    language: str,
) -> str:
    normalized = (
        language
        .strip()
        .lower()
    )

    if normalized not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported language '{normalized}'. "
                f"Supported languages: "
                f"{', '.join(sorted(SUPPORTED_LANGUAGES))}"
            ),
        )

    return normalized


def normalize_level(
    level: str,
) -> str:
    normalized = (
        level
        .strip()
        .upper()
    )

    if normalized not in SUPPORTED_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported learning level "
                f"'{normalized}'."
            ),
        )

    return normalized


def get_profile_for_user(
    db: Session,
    user_id: int,
    language: str,
) -> LearningProfile | None:
    return (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == user_id,
            LearningProfile.language == language,
        )
        .first()
    )


def get_or_create_profile(
    db: Session,
    user_id: int,
    language: str,
    level: str = "A1",
) -> LearningProfile:
    profile = get_profile_for_user(
        db=db,
        user_id=user_id,
        language=language,
    )

    if profile is not None:
        return profile

    profile = LearningProfile(
        user_id=user_id,
        language=language,
        level=level,
        progress=0.0,
    )

    db.add(profile)
    db.flush()

    return profile


# =========================================================
# Get all learning profiles
# =========================================================

@router.get(
    "/profiles",
    response_model=list[LearningProfileResponse],
)
def get_learning_profiles(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    profiles = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id
            == current_user.id
        )
        .order_by(
            LearningProfile.id.asc()
        )
        .all()
    )

    return profiles


# =========================================================
# Get current learning profile
# =========================================================

@router.get(
    "/current",
    response_model=LearningProfileResponse,
)
def get_current_learning_profile(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    language = normalize_language(
        current_user.learning_language
    )

    profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=language,
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Current learning profile not found."
            ),
        )

    return profile


# =========================================================
# Get a specific learning profile
# =========================================================

@router.get(
    "/profiles/{language}",
    response_model=LearningProfileResponse,
)
def get_learning_profile(
    language: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    normalized_language = normalize_language(
        language
    )

    profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=normalized_language,
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Learning profile not found."
            ),
        )

    return profile


# =========================================================
# Add a learning language
# =========================================================

@router.post(
    "/profiles",
    response_model=LearningProfileResponse,
)
def create_learning_profile(
    profile_data: LearningProfileCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    language = normalize_language(
        profile_data.language
    )

    level = normalize_level(
        profile_data.level
    )

    # -----------------------------------------------------
    # A user should not create a profile for their native
    # language.
    # -----------------------------------------------------

    native_language = normalize_language(
        current_user.native_language
    )

    if language == native_language:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot learn your "
                "native language."
            ),
        )

    existing_profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=language,
    )

    if existing_profile is not None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Learning profile already exists."
            ),
        )

    new_profile = LearningProfile(
        user_id=current_user.id,
        language=language,
        level=level,
        progress=0.0,
    )

    db.add(new_profile)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Learning profile already exists."
            ),
        )

    db.refresh(new_profile)

    return new_profile


# =========================================================
# Update learning profile
# =========================================================
#
# This endpoint updates only the selected profile.
#
# It does NOT change the user's current language.
# The current language is handled by /current/{language}.
#
# This is important because a user can have:
#
# English -> B1 -> 42%
# French  -> A2 -> 70%
# Japanese -> A1 -> 5%
#
# simultaneously.
# =========================================================

@router.put(
    "/profiles/{language}",
    response_model=LearningProfileResponse,
)
def update_learning_profile(
    language: str,
    profile_data: LearningProfileUpdate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    normalized_language = normalize_language(
        language
    )

    normalized_level = normalize_level(
        profile_data.level
    )

    native_language = normalize_language(
        current_user.native_language
    )

    if normalized_language == native_language:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot maintain a learning profile "
                "for your native language."
            ),
        )

    profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=normalized_language,
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Learning profile not found."
            ),
        )

    profile.level = normalized_level

    profile.progress = (
        profile_data.progress
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to update learning profile."
            ),
        )

    db.refresh(profile)

    return profile


# =========================================================
# Switch current learning language
# =========================================================
#
# This does not reset progress.
#
# It only changes:
#
# User.learning_language
#
# The user's profile for that language remains intact.
# =========================================================

@router.put(
    "/current/{language}"
)
def switch_learning_language(
    language: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    normalized_language = normalize_language(
        language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    if normalized_language == native_language:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot switch to your "
                "native language as a learning language."
            ),
        )

    profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=normalized_language,
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Learning profile not found for "
                f"language '{normalized_language}'."
            ),
        )

    current_user.learning_language = (
        normalized_language
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to switch learning language."
            ),
        )

    db.refresh(current_user)

    return {
        "message": (
            "Learning language switched successfully"
        ),
        "learning_language": (
            normalized_language
        ),
        "level": profile.level,
        "progress": profile.progress,
    }


# =========================================================
# Activate a learning language
# =========================================================
#
# This endpoint is provided as a clearer semantic alias
# for switching the current language.
#
# It is intentionally implemented through the same logic.
# =========================================================

@router.post(
    "/profiles/{language}/activate"
)
def activate_learning_profile(
    language: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    normalized_language = normalize_language(
        language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    if normalized_language == native_language:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot activate your "
                "native language as a learning language."
            ),
        )

    profile = get_profile_for_user(
        db=db,
        user_id=current_user.id,
        language=normalized_language,
    )

    if profile is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Learning profile not found."
            ),
        )

    current_user.learning_language = (
        normalized_language
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to activate learning profile."
            ),
        )

    db.refresh(current_user)

    return {
        "message": (
            "Learning profile activated successfully"
        ),
        "learning_language": (
            normalized_language
        ),
        "level": profile.level,
        "progress": profile.progress,
    }