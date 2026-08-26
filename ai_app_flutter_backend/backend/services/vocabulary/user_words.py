from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    User,
    VocabularyEntry,
    VocabularyForm,
    VocabularySense,
    VocabularySenseLocalization,
    VocabularyTranslation,
    Word,
)
from services.learning.profile import get_current_learning_profile


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _get_active_forms(entry_id: int, db: Session) -> list[VocabularyForm]:
    return (
        db.execute(
            select(VocabularyForm)
            .where(
                VocabularyForm.vocabulary_entry_id == entry_id,
                VocabularyForm.is_active.is_(True),
            )
            .order_by(VocabularyForm.id.asc())
            .limit(50)
        )
        .scalars()
        .all()
    )


def _get_native_translation(
    sense_id: int, language: str, db: Session
) -> VocabularyTranslation | None:
    primary = db.execute(
        select(VocabularyTranslation)
        .where(
            VocabularyTranslation.vocabulary_sense_id == sense_id,
            VocabularyTranslation.language == language,
            VocabularyTranslation.is_primary.is_(True),
        )
        .order_by(VocabularyTranslation.id.asc())
    ).scalar_one_or_none()
    if primary is not None:
        return primary
    return db.execute(
        select(VocabularyTranslation)
        .where(
            VocabularyTranslation.vocabulary_sense_id == sense_id,
            VocabularyTranslation.language == language,
        )
        .order_by(VocabularyTranslation.id.asc())
    ).scalar_one_or_none()


def save_ai_word_for_user(
    word: str,
    entry_id: int,
    sense_id: int,
    current_user: User,
    db: Session,
) -> Word:
    """Save an AI-detected word while preserving the chat flow's behavior."""
    profile = get_current_learning_profile(
        db=db,
        current_user=current_user,
        not_found_detail="Current learning profile not found.",
    )

    entry = db.execute(
        select(VocabularyEntry).where(
            VocabularyEntry.id == entry_id,
            VocabularyEntry.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if entry is None:
        raise RuntimeError("Vocabulary entry not found.")

    sense = db.execute(
        select(VocabularySense).where(
            VocabularySense.id == sense_id,
            VocabularySense.vocabulary_entry_id == entry.id,
            VocabularySense.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if sense is None:
        raise RuntimeError("Vocabulary sense not found.")

    normalized_word = _normalize_text(word) or word.strip().casefold()
    forms = _get_active_forms(entry.id, db)
    selected_form = next((form for form in forms if _normalize_text(form.form) == normalized_word), None)
    if selected_form is None:
        selected_form = next((form for form in forms if form.is_lemma), None)
    if selected_form is None and entry.word:
        selected_form = next((form for form in forms if _normalize_text(form.form) == _normalize_text(entry.word)), None)

    native_language = current_user.native_language.strip().lower()
    native_translation = _get_native_translation(sense.id, native_language, db)
    translation = native_translation.translation.strip() if native_translation is not None else None
    if not translation:
        localization = db.execute(
            select(VocabularySenseLocalization).where(
                VocabularySenseLocalization.vocabulary_sense_id == sense.id,
                VocabularySenseLocalization.language == native_language,
            )
        ).scalar_one_or_none()
        if localization is not None:
            translation = localization.meaning or localization.definition
            if translation:
                translation = translation.strip()
    translation = translation or word.strip()

    saved_word_text = selected_form.form.strip() if selected_form is not None else (entry.word.strip() if entry.word else entry.lemma.strip())
    existing = None
    if selected_form is not None:
        existing = db.execute(
            select(Word).where(
                Word.user_id == current_user.id,
                Word.learning_profile_id == profile.id,
                Word.vocabulary_form_id == selected_form.id,
            )
        ).scalar_one_or_none()
    if existing is None:
        existing = db.execute(
            select(Word)
            .where(
                Word.user_id == current_user.id,
                Word.learning_profile_id == profile.id,
                Word.vocabulary_entry_id == entry.id,
            )
            .order_by(Word.id.asc())
        ).scalars().first()
    if existing is not None:
        if not existing.translation or existing.translation == existing.word:
            existing.translation = translation
            db.commit()
            db.refresh(existing)
        return existing

    new_word = Word(
        word=saved_word_text,
        translation=translation,
        learned=False,
        user_id=current_user.id,
        learning_profile_id=profile.id,
        vocabulary_entry_id=entry.id,
        vocabulary_form_id=selected_form.id if selected_form is not None else None,
    )
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return new_word


