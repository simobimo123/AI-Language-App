from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from schemas import TutorExplanationLanguageUpdate, UserCreate, UserUpdate
from models import User
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])
password_hash = PasswordHash.recommended()

SUPPORTED_LANGUAGES = {"ar", "de", "en", "es", "fr", "id", "it", "ja", "ko", "nl", "pl", "pt", "ru", "th", "tr", "uk", "vi", "zh"}
SUPPORTED_LEVELS = {"PRE_A1", "A1", "A2", "B1", "B2", "C1", "C2"}
SUPPORTED_EXPLANATION_MODES = {"native", "learning"}


def normalize_language(language: str) -> str:
    normalized = language.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported language '{normalized}'. Supported languages: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    return normalized


def normalize_level(level: str) -> str:
    normalized = level.strip().upper()
    if normalized not in SUPPORTED_LEVELS:
        raise HTTPException(status_code=422, detail=f"Unsupported learning level '{normalized}'.")
    return normalized


def normalize_explanation_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_EXPLANATION_MODES:
        raise HTTPException(status_code=422, detail="Tutor explanation language mode must be 'native' or 'learning'.")
    return normalized


def user_response_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "is_active": user.is_active,
        "native_language": user.native_language,
        "learning_language": user.learning_language,
        "tutor_explanation_language_mode": user.tutor_explanation_language_mode,
    }


@router.post("")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    native_language = normalize_language(user.native_language)
    learning_language = normalize_language(user.learning_language)
    explanation_mode = normalize_explanation_mode(user.tutor_explanation_language_mode)
    if native_language == learning_language:
        raise HTTPException(status_code=400, detail="Native language and learning language must be different.")
    email = str(user.email).strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=400, detail="Email already registered.")
    new_user = User(
        name=user.name.strip(),
        email=email,
        password_hash=password_hash.hash(user.password),
        native_language=native_language,
        learning_language=learning_language,
        tutor_explanation_language_mode=explanation_mode,
        is_active=True,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User could not be created. The email may already be registered.")
    db.refresh(new_user)
    return {"message": "User created successfully", **user_response_dict(new_user)}


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return user_response_dict(current_user)


@router.put("/me")
def update_my_profile(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_native_language = normalize_language(user_data.native_language)
    new_learning_language = normalize_language(user_data.learning_language)
    if new_native_language == new_learning_language:
        raise HTTPException(status_code=400, detail="Native language and learning language must be different.")
    new_email = str(user_data.email).strip().lower()
    if db.query(User).filter(User.email == new_email, User.id != current_user.id).first() is not None:
        raise HTTPException(status_code=400, detail="Email already registered.")

    current_user.name = user_data.name.strip()
    current_user.email = new_email
    current_user.native_language = new_native_language
    current_user.learning_language = new_learning_language
    if user_data.tutor_explanation_language_mode is not None:
        current_user.tutor_explanation_language_mode = normalize_explanation_mode(
            user_data.tutor_explanation_language_mode
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User profile could not be updated.")
    db.refresh(current_user)
    return {"message": "User updated successfully", **user_response_dict(current_user)}


@router.patch("/me/tutor-explanation-language")
def update_tutor_explanation_language(
    data: TutorExplanationLanguageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.tutor_explanation_language_mode = normalize_explanation_mode(data.mode)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tutor explanation language could not be updated.")
    db.refresh(current_user)
    return {
        "message": "Tutor explanation language updated successfully",
        "tutor_explanation_language_mode": current_user.tutor_explanation_language_mode,
    }


@router.delete("/me")
def delete_my_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    db.delete(current_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete the user account.")
    return {"message": "User deleted successfully", "id": user_id}
