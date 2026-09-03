from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User, VocabularyExampleTranslation
from routers.auth import get_current_user
from services.ai.context import (
    find_vocabulary_entry,
    get_examples,
    get_senses,
    get_translation,
)
from services.ai.enrichment.service import enrich_vocabulary_on_demand
from services.ai.normalization import normalize_language
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request


router = APIRouter(
    prefix="/word-lookup",
    tags=["Word Lookup"],
)


class WordLookupRequest(BaseModel):
    word: str = Field(min_length=1, max_length=255)


def _example_translation(
    example_id: int,
    language: str,
    db: Session,
) -> str | None:
    statement = (
        select(VocabularyExampleTranslation)
        .where(
            VocabularyExampleTranslation.vocabulary_example_id == example_id,
            VocabularyExampleTranslation.language == language,
        )
        .order_by(
            VocabularyExampleTranslation.is_primary.desc(),
            VocabularyExampleTranslation.id.asc(),
        )
    )
    row = db.execute(statement).first()
    return row[0].translation if row else None


def _build_result(
    word: str,
    current_user: User,
    db: Session,
) -> dict:
    learning_language = normalize_language(current_user.learning_language)
    native_language = normalize_language(current_user.native_language)

    entry = find_vocabulary_entry(
        word=word,
        language=learning_language,
        db=db,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Word not found")

    senses = get_senses(entry.id, db)
    sense = senses[0] if senses else None
    if sense is None:
        raise HTTPException(status_code=404, detail="Word meaning not found")

    translation = get_translation(sense.id, native_language, db)
    examples = get_examples(sense.id, db)
    example = examples[0] if examples else None
    example_translation = (
        _example_translation(example.id, native_language, db)
        if example
        else None
    )

    return {
        "word": entry.word or entry.lemma,
        "lemma": entry.lemma,
        "learning_language": learning_language,
        "native_language": native_language,
        "translation": translation.translation if translation else None,
        "part_of_speech": entry.part_of_speech,
        "pronunciation": entry.pronunciation,
        "example_sentence": example.sentence if example else None,
        "example_translation": example_translation,
    }


@router.post("/")
def lookup_word(
    request: WordLookupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    word = request.word.strip()
    if not word:
        raise HTTPException(status_code=422, detail="Word cannot be empty")

    # Database is always the first source of truth. A tap on an already
    # complete vocabulary item does not consume an AI request.
    try:
        result = _build_result(word, current_user, db)
        if (
            result.get("translation")
            and result.get("example_sentence")
            and result.get("example_translation")
        ):
            return result
    except HTTPException:
        pass

    # If the item is missing or incomplete, enrich it once and persist it.
    # Future taps are then served from the database.
    check_rate_limit(current_user.id)
    reserve_ai_request(user_id=current_user.id, db=db)

    _, prompt_tokens, completion_tokens, total_tokens, _ = (
        enrich_vocabulary_on_demand(
            word=word,
            current_user=current_user,
            db=db,
        )
    )

    if prompt_tokens or completion_tokens or total_tokens:
        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db=db,
        )

    return _build_result(word, current_user, db)
