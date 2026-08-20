from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from schemas import WordCreate, WordResponse
from models import Word, User, LearningProfile
from database import get_db
from routers.auth import get_current_user


router = APIRouter(
    prefix="/words",
    tags=["Words"]
)


class WordStatusUpdate(BaseModel):
    learned: bool


# =========================
# Get current learning profile
# =========================

def get_current_profile(
    db: Session,
    current_user: User
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


# =========================
# Create word
# =========================

@router.post("/", response_model=WordResponse)
def create_word(
    word_data: WordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(
        db,
        current_user
    )

    new_word = Word(
        word=word_data.word,
        translation=word_data.translation,
        learned=False,
        user_id=current_user.id,
        learning_profile_id=profile.id
    )

    db.add(new_word)
    db.commit()
    db.refresh(new_word)

    return new_word


# =========================
# Get words
# =========================

@router.get("/", response_model=list[WordResponse])
def get_words(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(
        db,
        current_user
    )

    words = db.query(Word).filter(
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id
    ).all()

    return words


# =========================
# Update word
# =========================

@router.put("/{word_id}", response_model=WordResponse)
def update_word(
    word_id: int,
    word_data: WordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(
        db,
        current_user
    )

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id
    ).first()

    if word is None:
        raise HTTPException(
            status_code=404,
            detail="Word not found"
        )

    word.word = word_data.word
    word.translation = word_data.translation

    db.commit()
    db.refresh(word)

    return word


# =========================
# Update learned status
# =========================

@router.patch("/{word_id}", response_model=WordResponse)
def update_word_status(
    word_id: int,
    status_data: WordStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(
        db,
        current_user
    )

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id
    ).first()

    if word is None:
        raise HTTPException(
            status_code=404,
            detail="Word not found"
        )

    word.learned = status_data.learned

    db.commit()
    db.refresh(word)

    return word


# =========================
# Delete word
# =========================

@router.delete("/{word_id}")
def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(
        db,
        current_user
    )

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id
    ).first()

    if word is None:
        raise HTTPException(
            status_code=404,
            detail="Word not found"
        )

    db.delete(word)
    db.commit()

    return {
        "message": "Word deleted successfully"
    }