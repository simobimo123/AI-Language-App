import os

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from models import (
    User,
    VocabularyEntry,
    VocabularyExample,
    VocabularyForm,
    VocabularySense,
)
from routers.auth import get_current_user


# =========================================================
# Vocabulary editor authorization
# =========================================================

VOCABULARY_EDITOR_EMAILS = {
    email.strip().lower()
    for email in os.getenv(
        "VOCABULARY_EDITOR_EMAILS",
        "",
    ).split(",")
    if email.strip()
}


# =========================================================
# Authorization
# =========================================================

def require_vocabulary_editor(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:

    email = current_user.email.strip().lower()

    if email not in VOCABULARY_EDITOR_EMAILS:
        raise HTTPException(
            status_code=403,
            detail=(
                "Vocabulary database modification is restricted "
                "to authorized editors."
            ),
        )

    return current_user


# =========================================================
# Get helpers
# =========================================================

def get_entry_or_404(
    entry_id: int,
    db: Session,
) -> VocabularyEntry:

    entry = (
        db.query(VocabularyEntry)
        .filter(
            VocabularyEntry.id == entry_id,
            VocabularyEntry.is_active.is_(True),
        )
        .first()
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Vocabulary entry not found.",
        )

    return entry


def get_form_or_404(
    form_id: int,
    db: Session,
) -> VocabularyForm:

    form = (
        db.query(VocabularyForm)
        .filter(
            VocabularyForm.id == form_id,
            VocabularyForm.is_active.is_(True),
        )
        .first()
    )

    if form is None:
        raise HTTPException(
            status_code=404,
            detail="Vocabulary form not found.",
        )

    return form


def get_sense_or_404(
    sense_id: int,
    db: Session,
) -> VocabularySense:

    sense = (
        db.query(VocabularySense)
        .filter(
            VocabularySense.id == sense_id,
            VocabularySense.is_active.is_(True),
        )
        .first()
    )

    if sense is None:
        raise HTTPException(
            status_code=404,
            detail="Vocabulary sense not found.",
        )

    return sense


def get_example_or_404(
    example_id: int,
    db: Session,
) -> VocabularyExample:

    example = (
        db.query(VocabularyExample)
        .filter(
            VocabularyExample.id == example_id,
            VocabularyExample.is_active.is_(True),
        )
        .first()
    )

    if example is None:
        raise HTTPException(
            status_code=404,
            detail="Vocabulary example not found.",
        )

    return example
