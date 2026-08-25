from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from schemas import UserCreate, UserUpdate
from models import User
from database import get_db
from routers.auth import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


password_hash = PasswordHash.recommended()


# =========================================================
# Create user
# =========================================================

@router.post("")
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # -----------------------------------------------------
    # Native language and learning language
    # must be different
    # -----------------------------------------------------

    if user.native_language == user.learning_language:
        raise HTTPException(
            status_code=400,
            detail="Native language and learning language must be different"
        )

    hashed_password = password_hash.hash(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password,
        native_language=user.native_language,
        learning_language=user.learning_language
    )

    db.add(new_user)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "native_language": new_user.native_language,
        "learning_language": new_user.learning_language
    }


# =========================================================
# Get current user profile
# =========================================================

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "native_language": current_user.native_language,
        "learning_language": current_user.learning_language
    }


# =========================================================
# Update current user profile
# =========================================================

@router.put("/me")
def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Native language and learning language
    # must be different
    # -----------------------------------------------------

    if user_data.native_language == user_data.learning_language:
        raise HTTPException(
            status_code=400,
            detail="Native language and learning language must be different"
        )

    current_user.name = user_data.name
    current_user.email = user_data.email
    current_user.native_language = user_data.native_language
    current_user.learning_language = user_data.learning_language

    # -----------------------------------------------------
    # We intentionally do NOT create a LearningProfile here.
    #
    # The profile and its level are created after the
    # onboarding and placement test.
    # -----------------------------------------------------

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    db.refresh(current_user)

    return {
        "message": "User updated successfully",
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "native_language": current_user.native_language,
        "learning_language": current_user.learning_language
    }


# =========================================================
# Delete account
# =========================================================

@router.delete("/me")
def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id

    db.delete(current_user)

    db.commit()

    return {
        "message": "User deleted successfully",
        "id": user_id
    }
