from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from schemas import (
    WordCreate,
    WordFromVocabularyCreate,
    WordResponse,
)
from schemas.learning_bank import SentenceCreate, SentenceResponse
from models import (
    Word,
    User,
    VocabularyForm,
    VocabularyEntry,
    VocabularySense,
    VocabularyTranslation,
)
from database import get_db
from routers.auth import get_current_user
from services.learning.profile import get_current_learning_profile


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
    return get_current_learning_profile(
        db=db,
        current_user=current_user,
    )


# =========================
# Create manual word
# =========================

@router.post(
    "/",
    response_model=WordResponse
)
def create_word(
    word_data: WordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)

    new_word = Word(
        word=word_data.word,
        translation=word_data.translation,
        item_type="word",
        learned=False,
        user_id=current_user.id,
        learning_profile_id=profile.id,
        vocabulary_entry_id=None,
        vocabulary_form_id=None
    )

    db.add(new_word)
    db.commit()
    db.refresh(new_word)

    return new_word


# =========================
# Save word from global vocabulary
# =========================

@router.post(
    "/from-vocabulary",
    response_model=WordResponse
)
def save_word_from_vocabulary(
    word_data: WordFromVocabularyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)

    form = db.query(VocabularyForm).filter(
        VocabularyForm.id == word_data.vocabulary_form_id,
        VocabularyForm.is_active.is_(True)
    ).first()

    if form is None:
        raise HTTPException(status_code=404, detail="Vocabulary form not found")

    entry = db.query(VocabularyEntry).filter(
        VocabularyEntry.id == form.vocabulary_entry_id,
        VocabularyEntry.is_active.is_(True)
    ).first()

    if entry is None:
        raise HTTPException(status_code=404, detail="Vocabulary entry not found")

    native_language = current_user.native_language.strip().lower()

    translation_result = (
        db.query(VocabularyTranslation)
        .join(VocabularySense, VocabularySense.id == VocabularyTranslation.vocabulary_sense_id)
        .filter(
            VocabularySense.vocabulary_entry_id == entry.id,
            VocabularySense.is_active.is_(True),
            VocabularyTranslation.language == native_language
        )
        .order_by(
            VocabularyTranslation.is_primary.desc(),
            VocabularyTranslation.id.asc()
        )
        .first()
    )

    if translation_result is None:
        raise HTTPException(
            status_code=404,
            detail="Translation for the user's native language was not found"
        )

    existing = db.query(Word).filter(
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.vocabulary_form_id == form.id,
        Word.item_type == "word"
    ).first()

    if existing is not None:
        return existing

    new_word = Word(
        word=form.form,
        translation=translation_result.translation,
        item_type="word",
        learned=False,
        user_id=current_user.id,
        learning_profile_id=profile.id,
        vocabulary_entry_id=entry.id,
        vocabulary_form_id=form.id
    )

    db.add(new_word)
    db.commit()
    db.refresh(new_word)

    return new_word


# =========================
# Get words only
# =========================

@router.get(
    "/",
    response_model=list[WordResponse]
)
def get_words(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)

    words = db.query(Word).filter(
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "word"
    ).order_by(Word.id.desc()).all()

    return words


# =========================
# Sentences in the same bank
# =========================

@router.post(
    "/sentences",
    response_model=SentenceResponse
)
def create_sentence(
    sentence_data: SentenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)
    sentence_text = sentence_data.sentence.strip()
    translation = sentence_data.translation.strip()

    existing = db.query(Word).filter(
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "sentence",
        Word.word == sentence_text,
        Word.translation == translation,
    ).first()

    if existing is not None:
        return {
            "id": existing.id,
            "sentence": existing.word,
            "translation": existing.translation,
            "learned": existing.learned,
            "user_id": existing.user_id,
            "learning_profile_id": existing.learning_profile_id,
        }

    new_sentence = Word(
        word=sentence_text,
        translation=translation,
        item_type="sentence",
        learned=False,
        user_id=current_user.id,
        learning_profile_id=profile.id,
        vocabulary_entry_id=None,
        vocabulary_form_id=None,
    )

    db.add(new_sentence)
    db.commit()
    db.refresh(new_sentence)

    return {
        "id": new_sentence.id,
        "sentence": new_sentence.word,
        "translation": new_sentence.translation,
        "learned": new_sentence.learned,
        "user_id": new_sentence.user_id,
        "learning_profile_id": new_sentence.learning_profile_id,
    }


@router.get(
    "/sentences",
    response_model=list[SentenceResponse]
)
def get_sentences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)
    rows = db.query(Word).filter(
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "sentence"
    ).order_by(Word.id.desc()).all()

    return [
        {
            "id": row.id,
            "sentence": row.word,
            "translation": row.translation,
            "learned": row.learned,
            "user_id": row.user_id,
            "learning_profile_id": row.learning_profile_id,
        }
        for row in rows
    ]


@router.patch(
    "/sentences/{sentence_id}",
    response_model=SentenceResponse
)
def update_sentence_status(
    sentence_id: int,
    status_data: WordStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)
    sentence = db.query(Word).filter(
        Word.id == sentence_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "sentence"
    ).first()

    if sentence is None:
        raise HTTPException(status_code=404, detail="Sentence not found")

    sentence.learned = status_data.learned
    db.commit()
    db.refresh(sentence)

    return {
        "id": sentence.id,
        "sentence": sentence.word,
        "translation": sentence.translation,
        "learned": sentence.learned,
        "user_id": sentence.user_id,
        "learning_profile_id": sentence.learning_profile_id,
    }


@router.delete("/sentences/{sentence_id}")
def delete_sentence(
    sentence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)
    sentence = db.query(Word).filter(
        Word.id == sentence_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "sentence"
    ).first()

    if sentence is None:
        raise HTTPException(status_code=404, detail="Sentence not found")

    db.delete(sentence)
    db.commit()

    return {"message": "Sentence deleted successfully"}


# =========================
# Update word
# =========================

@router.put(
    "/{word_id}",
    response_model=WordResponse
)
def update_word(
    word_id: int,
    word_data: WordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "word"
    ).first()

    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    word.word = word_data.word
    word.translation = word_data.translation

    db.commit()
    db.refresh(word)

    return word


# =========================
# Update word learned status
# =========================

@router.patch(
    "/{word_id}",
    response_model=WordResponse
)
def update_word_status(
    word_id: int,
    status_data: WordStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = get_current_profile(db, current_user)

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "word"
    ).first()

    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

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
    profile = get_current_profile(db, current_user)

    word = db.query(Word).filter(
        Word.id == word_id,
        Word.user_id == current_user.id,
        Word.learning_profile_id == profile.id,
        Word.item_type == "word"
    ).first()

    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    db.delete(word)
    db.commit()

    return {"message": "Word deleted successfully"}
