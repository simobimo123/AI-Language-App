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
    LearningProfile,
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


def get_or_create_learning_profile(
    db: Session,
    user_id: int,
    language: str,
    level: str = "A1",
) -> LearningProfile:
    """
    Return the user's profile for a language.

    Important:
    We never delete an existing profile just because the user
    changes their current learning language.

    This allows one user to maintain progress in multiple
    languages.

    Example:

        Arabic -> learning profile
        English -> learning profile
        Japanese -> learning profile
    """

    existing_profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == user_id,
            LearningProfile.language == language,
        )
        .first()
    )

    if existing_profile is not None:
        return existing_profile

    profile = LearningProfile(
        user_id=user_id,
        language=language,
        level=level,
        progress=0.0,
    )

    db.add(profile)

    # The caller may need the profile ID immediately.
    db.flush()

    return profile


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

    learning_level = normalize_level(
        user.learning_level
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
        db.flush()

        # -------------------------------------------------
        # Create the initial learning profile.
        #
        # This uses the level supplied during registration.
        #
        # Placement can later replace this level with the
        # measured level.
        # -------------------------------------------------

        learning_profile = LearningProfile(
            user_id=new_user.id,
            language=learning_language,
            level=learning_level,
            progress=0.0,
        )

        db.add(learning_profile)

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
        "learning_level": learning_level,
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

    old_learning_language = (
        current_user.learning_language
    )

    # -----------------------------------------------------
    # Update the user.
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
        # -------------------------------------------------
        # When the user switches to another learning
        # language, ensure that a profile exists for it.
        #
        # We do NOT delete the previous language profile.
        # -------------------------------------------------

        if (
            old_learning_language
            != new_learning_language
        ):
            get_or_create_learning_profile(
                db=db,
                user_id=current_user.id,
                language=new_learning_language,
                level="A1",
            )

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