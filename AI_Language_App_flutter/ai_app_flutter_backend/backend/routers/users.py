from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from schemas import (
    UserCreate,
    UserUpdate,
)
from models import (
    User,
)
from database import get_db
from routers.auth import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


password_hash = PasswordHash.recommended()


# =========================================================
# Supported languages
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


def user_response_dict(
    user: User,
) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
        "native_language": user.native_language,
        "learning_language": user.learning_language,
    }


# =========================================================
# Create user
# =========================================================
#
# IMPORTANT:
#
# Creating an account must NOT create a LearningProfile.
#
# The learning profile is created only after the Placement
# Test has determined the user's actual level.
# =========================================================

@router.post("")
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    native_language = normalize_language(
        user.native_language
    )

    learning_language = normalize_language(
        user.learning_language
    )

    # -----------------------------------------------------
    # Native and learning languages must differ.
    # -----------------------------------------------------

    if native_language == learning_language:
        raise HTTPException(
            status_code=400,
            detail=(
                "Native language and learning language "
                "must be different."
            ),
        )

    email = (
        str(user.email)
        .strip()
        .lower()
    )

    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Email already registered.",
        )

    hashed_password = password_hash.hash(
        user.password
    )

    new_user = User(
        name=user.name.strip(),
        email=email,
        password_hash=hashed_password,
        native_language=native_language,
        learning_language=learning_language,
        is_active=True,
    )

    db.add(new_user)

    try:
        # -------------------------------------------------
        # Create ONLY the user.
        #
        # No LearningProfile is created here.
        # The Placement Test will create it later.
        # -------------------------------------------------

        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "User could not be created. "
                "The email may already be registered."
            ),
        )

    db.refresh(new_user)

    return {
        "message": "User created successfully",
        **user_response_dict(new_user),
    }


# =========================================================
# Get current user profile
# =========================================================

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(
        get_current_user
    ),
):
    return user_response_dict(
        current_user
    )


# =========================================================
# Update current user profile
# =========================================================
#
# This endpoint updates only the User record.
#
# IMPORTANT:
#
# It must NOT create a LearningProfile.
#
# During onboarding the user chooses the languages first,
# then the Placement Test creates the learning profile.
# =========================================================

@router.put("/me")
def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    new_native_language = normalize_language(
        user_data.native_language
    )

    new_learning_language = normalize_language(
        user_data.learning_language
    )

    # -----------------------------------------------------
    # Native and learning languages must differ.
    # -----------------------------------------------------

    if (
        new_native_language
        == new_learning_language
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Native language and learning language "
                "must be different."
            ),
        )

    new_email = (
        str(user_data.email)
        .strip()
        .lower()
    )

    # -----------------------------------------------------
    # Prevent changing the email to another user's email.
    # -----------------------------------------------------

    existing_email_user = (
        db.query(User)
        .filter(
            User.email == new_email,
            User.id != current_user.id,
        )
        .first()
    )

    if existing_email_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Email already registered.",
        )

    # -----------------------------------------------------
    # Update ONLY the user.
    #
    # No LearningProfile is created here.
    # -----------------------------------------------------

    current_user.name = (
        user_data.name.strip()
    )

    current_user.email = new_email

    current_user.native_language = (
        new_native_language
    )

    current_user.learning_language = (
        new_learning_language
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "User profile could not be updated."
            ),
        )

    db.refresh(current_user)

    return {
        "message": "User updated successfully",
        **user_response_dict(current_user),
    }


# =========================================================
# Delete account
# =========================================================

@router.delete("/me")
def delete_my_account(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    user_id = current_user.id

    db.delete(current_user)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to delete the user account."
            ),
        )

    return {
        "message": "User deleted successfully",
        "id": user_id,
    }