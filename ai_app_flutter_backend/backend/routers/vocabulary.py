import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db

from models import (
    User,
    VocabularyEntry,
    VocabularyRelation,
    VocabularyForm,
    VocabularySense,
    VocabularyCEFRAssessment,
    VocabularySenseLocalization,
    VocabularyTranslation,
    VocabularyExample,
    VocabularyExampleTranslation,
    VocabularyMedia,
)

from schemas import (
    VocabularyEntryCreate,
    VocabularyEntryResponse,
    VocabularyLocalizedEntryResponse,
    VocabularyLocalizedSenseResponse,
    VocabularyLocalizedExampleResponse,
    VocabularyRelationCreate,
    VocabularyRelationResponse,
    VocabularyFormCreate,
    VocabularyFormResponse,
    VocabularySenseCreate,
    VocabularySenseResponse,
    VocabularyCEFRAssessmentCreate,
    VocabularyCEFRAssessmentResponse,
    VocabularySenseLocalizationCreate,
    VocabularySenseLocalizationResponse,
    VocabularyTranslationCreate,
    VocabularyTranslationResponse,
    VocabularyExampleCreate,
    VocabularyExampleResponse,
    VocabularyExampleTranslationCreate,
    VocabularyExampleTranslationResponse,
    VocabularyMediaCreate,
    VocabularyMediaResponse,
)

from routers.auth import get_current_user


router = APIRouter(
    prefix="/vocabulary",
    tags=["Vocabulary"],
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
# Normalization helpers
# =========================================================

def normalize_language(
    language: str,
) -> str:

    normalized = language.strip().lower()

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

    normalized = level.strip().upper()

    if normalized not in SUPPORTED_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported level '{normalized}'. "
                f"Supported levels: "
                f"{', '.join(sorted(SUPPORTED_LEVELS))}"
            ),
        )

    return normalized


def normalize_form(
    form: str,
) -> str:

    return " ".join(
        form.strip().casefold().split()
    )


def normalize_lemma(
    lemma: str,
) -> str:

    return " ".join(
        lemma.strip().casefold().split()
    )


def clean_optional_text(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    value = value.strip()

    return value if value else None


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


# =========================================================
# Entry lookup
# =========================================================

@router.get(
    "/lookup",
    response_model=list[VocabularyEntryResponse],
)
def lookup_vocabulary(
    word: str = Query(
        ...,
        min_length=1,
        max_length=255,
    ),
    language: str = Query(
        ...,
        min_length=2,
        max_length=10,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    normalized_language = normalize_language(
        language
    )

    search_value = normalize_lemma(
        word
    )

    entries = (
        db.query(VocabularyEntry)
        .filter(
            VocabularyEntry.language
            == normalized_language,
            VocabularyEntry.is_active.is_(True),
        )
        .filter(
            (
                VocabularyEntry.normalized_lemma
                == search_value
            )
            |
            (
                VocabularyEntry.lemma.ilike(
                    word.strip()
                )
            )
            |
            (
                VocabularyEntry.word.ilike(
                    word.strip()
                )
            )
        )
        .order_by(
            VocabularyEntry.id.asc()
        )
        .limit(limit)
        .all()
    )

    return entries


# =========================================================
# User-localized vocabulary
# =========================================================

@router.get(
    "/entries/for-user",
    response_model=list[VocabularyLocalizedEntryResponse],
)
def list_vocabulary_for_user(
    level: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    part_of_speech: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    learning_language = normalize_language(
        current_user.learning_language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    normalized_level = None

    if level:
        normalized_level = normalize_level(
            level
        )

    query = (
        db.query(VocabularyEntry)
        .filter(
            VocabularyEntry.language
            == learning_language,
            VocabularyEntry.is_active.is_(True),
        )
    )

    if part_of_speech:
        query = query.filter(
            VocabularyEntry.part_of_speech
            == part_of_speech.strip()
        )

    if search:
        normalized_search = normalize_lemma(
            search
        )

        query = query.filter(
            (
                VocabularyEntry.normalized_lemma
                .ilike(
                    f"%{normalized_search}%"
                )
            )
            |
            (
                VocabularyEntry.lemma
                .ilike(
                    f"%{search.strip()}%"
                )
            )
        )

    if normalized_level:

        query = (
            query.join(
                VocabularySense,
                VocabularySense.vocabulary_entry_id
                == VocabularyEntry.id,
            )
            .filter(
                VocabularySense.cefr_level
                == normalized_level,
                VocabularySense.is_active.is_(True),
            )
            .distinct()
        )

    entries = (
        query
        .order_by(
            VocabularyEntry.id.asc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not entries:
        return []

    entry_ids = [
        entry.id
        for entry in entries
    ]

    # -----------------------------------------------------
    # Senses
    # -----------------------------------------------------

    senses_query = (
        db.query(VocabularySense)
        .filter(
            VocabularySense.vocabulary_entry_id.in_(
                entry_ids
            ),
            VocabularySense.is_active.is_(True),
        )
    )

    if normalized_level:

        senses_query = (
            senses_query.filter(
                VocabularySense.cefr_level
                == normalized_level
            )
        )

    senses = (
        senses_query
        .order_by(
            VocabularySense.id.asc()
        )
        .all()
    )

    sense_ids = [
        sense.id
        for sense in senses
    ]

    # -----------------------------------------------------
    # Localizations
    # -----------------------------------------------------

    localizations = []

    if sense_ids:

        localization_languages = {
            learning_language,
            native_language,
        }

        localizations = (
            db.query(
                VocabularySenseLocalization
            )
            .filter(
                VocabularySenseLocalization
                .vocabulary_sense_id
                .in_(sense_ids),
                VocabularySenseLocalization
                .language
                .in_(
                    localization_languages
                ),
            )
            .all()
        )

    localization_by_key: dict[
        tuple[int, str],
        VocabularySenseLocalization,
    ] = {}

    for localization in localizations:

        localization_by_key[
            (
                localization.vocabulary_sense_id,
                normalize_language(
                    localization.language
                ),
            )
        ] = localization

    # -----------------------------------------------------
    # Translations
    # -----------------------------------------------------

    translations = []

    if sense_ids:

        translations = (
            db.query(
                VocabularyTranslation
            )
            .filter(
                VocabularyTranslation
                .vocabulary_sense_id
                .in_(sense_ids),
                VocabularyTranslation.language
                == native_language,
            )
            .order_by(
                VocabularyTranslation
                .is_primary
                .desc(),
                VocabularyTranslation
                .id
                .asc(),
            )
            .all()
        )

    translation_by_sense: dict[
        int,
        VocabularyTranslation,
    ] = {}

    for translation in translations:

        if (
            translation.vocabulary_sense_id
            not in translation_by_sense
        ):
            translation_by_sense[
                translation.vocabulary_sense_id
            ] = translation

    # -----------------------------------------------------
    # Examples
    # -----------------------------------------------------

    examples = []

    if sense_ids:

        examples = (
            db.query(
                VocabularyExample
            )
            .filter(
                VocabularyExample
                .vocabulary_sense_id
                .in_(sense_ids),
                VocabularyExample
                .is_active.is_(True),
            )
            .order_by(
                VocabularyExample.id.asc()
            )
            .all()
        )

    examples_by_sense: dict[
        int,
        list[VocabularyExample],
    ] = {}

    for example in examples:

        examples_by_sense.setdefault(
            example.vocabulary_sense_id,
            [],
        ).append(
            example
        )

    # -----------------------------------------------------
    # Example translations
    # -----------------------------------------------------

    example_ids = [
        example.id
        for example in examples
    ]

    example_translations = []

    if example_ids:

        example_translations = (
            db.query(
                VocabularyExampleTranslation
            )
            .filter(
                VocabularyExampleTranslation
                .vocabulary_example_id
                .in_(example_ids),
                VocabularyExampleTranslation
                .language
                == native_language,
            )
            .order_by(
                VocabularyExampleTranslation
                .is_primary
                .desc(),
                VocabularyExampleTranslation
                .id
                .asc(),
            )
            .all()
        )

    example_translation_by_example: dict[
        int,
        VocabularyExampleTranslation,
    ] = {}

    for translation in example_translations:

        if (
            translation.vocabulary_example_id
            not in example_translation_by_example
        ):
            example_translation_by_example[
                translation.vocabulary_example_id
            ] = translation

    # -----------------------------------------------------
    # Group senses by entry
    # -----------------------------------------------------

    senses_by_entry: dict[
        int,
        list[VocabularySense],
    ] = {}

    for sense in senses:

        senses_by_entry.setdefault(
            sense.vocabulary_entry_id,
            [],
        ).append(
            sense
        )

    # -----------------------------------------------------
    # Build response
    # -----------------------------------------------------

    result = []

    for entry in entries:

        localized_senses = []

        for sense in senses_by_entry.get(
            entry.id,
            [],
        ):

            learning_localization = (
                localization_by_key.get(
                    (
                        sense.id,
                        learning_language,
                    )
                )
            )

            native_localization = (
                localization_by_key.get(
                    (
                        sense.id,
                        native_language,
                    )
                )
            )

            native_translation = (
                translation_by_sense.get(
                    sense.id
                )
            )

            localized_examples = []

            for example in (
                examples_by_sense.get(
                    sense.id,
                    [],
                )
            ):

                example_translation = (
                    example_translation_by_example.get(
                        example.id
                    )
                )

                localized_examples.append(
                    VocabularyLocalizedExampleResponse(
                        id=example.id,
                        sentence=example.sentence,
                        level=example.level,
                        translation_language=(
                            native_language
                        ),
                        translation=(
                            example_translation.translation
                            if example_translation
                            else None
                        ),
                    )
                )

            localized_senses.append(
                VocabularyLocalizedSenseResponse(
                    id=sense.id,
                    vocabulary_entry_id=(
                        sense.vocabulary_entry_id
                    ),
                    cefr_level=sense.cefr_level,
                    frequency_rank=sense.frequency_rank,
                    learning_language=(
                        learning_language
                    ),
                    native_language=(
                        native_language
                    ),
                    learning_meaning=(
                        learning_localization.meaning
                        if learning_localization
                        else None
                    ),
                    learning_definition=(
                        learning_localization.definition
                        if learning_localization
                        else None
                    ),
                    native_meaning=(
                        native_localization.meaning
                        if native_localization
                        else None
                    ),
                    native_definition=(
                        native_localization.definition
                        if native_localization
                        else None
                    ),
                    native_translation=(
                        native_translation.translation
                        if native_translation
                        else None
                    ),
                    enrichment_status=(
                        sense.enrichment_status
                    ),
                    quality_score=(
                        sense.quality_score
                    ),
                    examples=localized_examples,
                )
            )

        result.append(
            VocabularyLocalizedEntryResponse(
                id=entry.id,
                language=entry.language,
                lemma=entry.lemma,
                normalized_lemma=(
                    entry.normalized_lemma
                ),
                word=entry.word,
                part_of_speech=(
                    entry.part_of_speech
                ),
                pronunciation=(
                    entry.pronunciation
                ),
                frequency_rank=(
                    entry.frequency_rank
                ),
                source=entry.source,
                source_version=(
                    entry.source_version
                ),
                learning_language=(
                    learning_language
                ),
                native_language=(
                    native_language
                ),
                enrichment_status=(
                    entry.enrichment_status
                ),
                quality_score=None,
                senses=localized_senses,
            )
        )

    return result


# =========================================================
# Get one entry
# =========================================================

@router.get(
    "/entries/{entry_id}",
    response_model=VocabularyEntryResponse,
)
def get_vocabulary_entry(
    entry_id: int,
    db: Session = Depends(get_db),
):
    return get_entry_or_404(
        entry_id,
        db,
    )


# =========================================================
# Create entry
# =========================================================

@router.post(
    "/entries",
    response_model=VocabularyEntryResponse,
)
def create_vocabulary_entry(
    data: VocabularyEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    language = normalize_language(
        data.language
    )

    lemma = data.lemma.strip()

    if not lemma:
        raise HTTPException(
            status_code=422,
            detail="Lemma cannot be empty.",
        )

    part_of_speech = clean_optional_text(
        data.part_of_speech
    )

    normalized_lemma = (
        clean_optional_text(
            data.normalized_lemma
        )
        or normalize_lemma(lemma)
    )

    existing = (
        db.query(VocabularyEntry)
        .filter(
            VocabularyEntry.language
            == language,
            VocabularyEntry.lemma
            == lemma,
            VocabularyEntry.part_of_speech
            == part_of_speech,
        )
        .first()
    )

    if existing is not None:

        if not existing.is_active:
            existing.is_active = True

        if data.word:
            existing.word = (
                data.word.strip()
            )

        if data.normalized_lemma:
            existing.normalized_lemma = (
                normalized_lemma
            )

        if data.pronunciation:
            existing.pronunciation = (
                data.pronunciation.strip()
            )

        if data.frequency_rank is not None:
            existing.frequency_rank = (
                data.frequency_rank
            )

        if data.source:
            existing.source = (
                data.source.strip()
            )

        if data.source_version:
            existing.source_version = (
                data.source_version.strip()
            )

        db.commit()
        db.refresh(existing)

        return existing

    entry = VocabularyEntry(
        language=language,
        lemma=lemma,
        normalized_lemma=normalized_lemma,
        word=(
            data.word.strip()
            if data.word
            else None
        ),
        part_of_speech=part_of_speech,
        pronunciation=(
            data.pronunciation.strip()
            if data.pronunciation
            else None
        ),
        frequency_rank=data.frequency_rank,
        source=(
            data.source.strip()
            if data.source
            else None
        ),
        source_version=(
            data.source_version.strip()
            if data.source_version
            else None
        ),
        enrichment_status="partial",
        is_active=True,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry


# =========================================================
# List entries
# =========================================================

@router.get(
    "/entries",
    response_model=list[VocabularyEntryResponse],
)
def list_vocabulary_entries(
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    level: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    part_of_speech: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    enrichment_status: str | None = Query(
        default=None,
        pattern=(
            r"^(partial|complete|needs_review)$"
        ),
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    query = (
        db.query(VocabularyEntry)
        .filter(
            VocabularyEntry.is_active.is_(True)
        )
    )

    if language:

        query = query.filter(
            VocabularyEntry.language
            == normalize_language(language)
        )

    if part_of_speech:

        query = query.filter(
            VocabularyEntry.part_of_speech
            == part_of_speech.strip()
        )

    if search:

        normalized_search = (
            normalize_lemma(search)
        )

        query = query.filter(
            (
                VocabularyEntry
                .normalized_lemma
                .ilike(
                    f"%{normalized_search}%"
                )
            )
            |
            (
                VocabularyEntry
                .lemma
                .ilike(
                    f"%{search.strip()}%"
                )
            )
        )

    if enrichment_status:

        query = query.filter(
            VocabularyEntry.enrichment_status
            == enrichment_status
        )

    if level:

        normalized_level = (
            normalize_level(level)
        )

        query = (
            query.join(
                VocabularySense,
                VocabularySense.vocabulary_entry_id
                == VocabularyEntry.id,
            )
            .filter(
                VocabularySense.cefr_level
                == normalized_level,
                VocabularySense.is_active.is_(True),
            )
            .distinct()
        )

    return (
        query
        .order_by(
            VocabularyEntry.id.asc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


# =========================================================
# Relations
# =========================================================

@router.post(
    "/entries/{entry_id}/relations",
    response_model=VocabularyRelationResponse,
)
def create_vocabulary_relation(
    entry_id: int,
    data: VocabularyRelationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    source_entry = get_entry_or_404(
        entry_id,
        db,
    )

    target_entry = get_entry_or_404(
        data.target_entry_id,
        db,
    )

    if source_entry.id == target_entry.id:

        raise HTTPException(
            status_code=400,
            detail=(
                "An entry cannot be related "
                "to itself."
            ),
        )

    if source_entry.language != target_entry.language:

        raise HTTPException(
            status_code=400,
            detail=(
                "Vocabulary relations must connect "
                "entries from the same language."
            ),
        )

    if data.source_sense_id is not None:

        source_sense = get_sense_or_404(
            data.source_sense_id,
            db,
        )

        if (
            source_sense.vocabulary_entry_id
            != source_entry.id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "source_sense_id does not belong "
                    "to source_entry_id."
                ),
            )

    if data.target_sense_id is not None:

        target_sense = get_sense_or_404(
            data.target_sense_id,
            db,
        )

        if (
            target_sense.vocabulary_entry_id
            != target_entry.id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "target_sense_id does not belong "
                    "to target_entry_id."
                ),
            )

    relation_type = (
        data.relation_type
        .strip()
        .lower()
    )

    if not relation_type:

        raise HTTPException(
            status_code=422,
            detail="Relation type cannot be empty.",
        )

    existing = (
        db.query(VocabularyRelation)
        .filter(
            VocabularyRelation.source_entry_id
            == source_entry.id,
            VocabularyRelation.target_entry_id
            == target_entry.id,
            VocabularyRelation.relation_type
            == relation_type,
        )
        .first()
    )

    if existing is not None:

        existing.source_sense_id = (
            data.source_sense_id
        )

        existing.target_sense_id = (
            data.target_sense_id
        )

        existing.is_bidirectional = (
            data.is_bidirectional
        )

        existing.source = (
            clean_optional_text(
                data.source
            )
        )

        existing.source_version = (
            clean_optional_text(
                data.source_version
            )
        )

        existing.is_active = True

        db.commit()
        db.refresh(existing)

        return existing

    relation = VocabularyRelation(
        source_entry_id=source_entry.id,
        target_entry_id=target_entry.id,
        source_sense_id=data.source_sense_id,
        target_sense_id=data.target_sense_id,
        relation_type=relation_type,
        language=source_entry.language,
        is_bidirectional=(
            data.is_bidirectional
        ),
        source=clean_optional_text(
            data.source
        ),
        source_version=clean_optional_text(
            data.source_version
        ),
        is_active=True,
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)

    return relation


@router.get(
    "/entries/{entry_id}/relations",
    response_model=list[VocabularyRelationResponse],
)
def list_vocabulary_relations(
    entry_id: int,
    relation_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    direction: str = Query(
        default="outgoing",
        pattern=r"^(outgoing|incoming|all)$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    entry = get_entry_or_404(
        entry_id,
        db,
    )

    if direction == "outgoing":

        query = (
            db.query(
                VocabularyRelation
            )
            .filter(
                VocabularyRelation
                .source_entry_id
                == entry.id,
                VocabularyRelation
                .is_active.is_(True),
            )
        )

    elif direction == "incoming":

        query = (
            db.query(
                VocabularyRelation
            )
            .filter(
                VocabularyRelation
                .target_entry_id
                == entry.id,
                VocabularyRelation
                .is_active.is_(True),
            )
        )

    else:

        query = (
            db.query(
                VocabularyRelation
            )
            .filter(
                (
                    VocabularyRelation
                    .source_entry_id
                    == entry.id
                )
                |
                (
                    VocabularyRelation
                    .target_entry_id
                    == entry.id
                ),
                VocabularyRelation
                .is_active.is_(True),
            )
        )

    if relation_type:

        query = query.filter(
            VocabularyRelation
            .relation_type
            == relation_type.strip().lower()
        )

    return (
        query
        .order_by(
            VocabularyRelation.id.asc()
        )
        .all()
    )


# =========================================================
# Forms
# =========================================================

@router.post(
    "/entries/{entry_id}/forms",
    response_model=VocabularyFormResponse,
)
def create_vocabulary_form(
    entry_id: int,
    data: VocabularyFormCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    entry = get_entry_or_404(
        entry_id,
        db,
    )

    form_value = data.form.strip()

    if not form_value:

        raise HTTPException(
            status_code=422,
            detail="Form cannot be empty.",
        )

    normalized_form = (
        data.normalized_form.strip()
        if data.normalized_form
        else normalize_form(form_value)
    )

    existing = (
        db.query(VocabularyForm)
        .filter(
            VocabularyForm.vocabulary_entry_id
            == entry.id,
            VocabularyForm.form
            == form_value,
        )
        .first()
    )

    if existing is not None:

        existing.normalized_form = (
            normalized_form
        )

        if (
            data.grammatical_features
            is not None
        ):
            existing.grammatical_features = (
                data.grammatical_features
            )

        if data.form_type is not None:
            existing.form_type = (
                data.form_type.strip()
            )

        existing.is_lemma = data.is_lemma

        if data.source is not None:
            existing.source = (
                data.source.strip()
            )

        if data.source_version is not None:
            existing.source_version = (
                data.source_version.strip()
            )

        existing.is_active = True

        db.commit()
        db.refresh(existing)

        return existing

    form = VocabularyForm(
        vocabulary_entry_id=entry.id,
        form=form_value,
        normalized_form=normalized_form,
        grammatical_features=(
            data.grammatical_features
        ),
        form_type=(
            data.form_type.strip()
            if data.form_type
            else None
        ),
        is_lemma=data.is_lemma,
        source=(
            data.source.strip()
            if data.source
            else None
        ),
        source_version=(
            data.source_version.strip()
            if data.source_version
            else None
        ),
        is_active=True,
    )

    db.add(form)
    db.commit()
    db.refresh(form)

    return form


@router.get(
    "/entries/{entry_id}/forms",
    response_model=list[VocabularyFormResponse],
)
def list_vocabulary_forms(
    entry_id: int,
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    form_type: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    entry = get_entry_or_404(
        entry_id,
        db,
    )

    query = (
        db.query(VocabularyForm)
        .filter(
            VocabularyForm.vocabulary_entry_id
            == entry.id,
            VocabularyForm.is_active.is_(True),
        )
    )

    if search:

        normalized_search = normalize_form(
            search
        )

        query = query.filter(
            VocabularyForm
            .normalized_form
            .ilike(
                f"%{normalized_search}%"
            )
        )

    if form_type:

        query = query.filter(
            VocabularyForm.form_type
            == form_type.strip()
        )

    return (
        query
        .order_by(
            VocabularyForm.id.asc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get(
    "/forms/lookup/{form_text}",
    response_model=list[VocabularyFormResponse],
)
def lookup_vocabulary_forms(
    form_text: str,
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    normalized_form = normalize_form(
        form_text
    )

    query = (
        db.query(
            VocabularyForm
        )
        .join(
            VocabularyEntry,
            VocabularyEntry.id
            == VocabularyForm.vocabulary_entry_id,
        )
        .filter(
            VocabularyForm
            .normalized_form
            == normalized_form,
            VocabularyForm
            .is_active.is_(True),
            VocabularyEntry
            .is_active.is_(True),
        )
    )

    if language:

        query = query.filter(
            VocabularyEntry.language
            == normalize_language(
                language
            )
        )

    return (
        query
        .order_by(
            VocabularyForm.id.asc()
        )
        .limit(limit)
        .all()
    )


@router.get(
    "/forms/{form_id}",
    response_model=VocabularyFormResponse,
)
def get_vocabulary_form(
    form_id: int,
    db: Session = Depends(get_db),
):
    return get_form_or_404(
        form_id,
        db,
    )


# =========================================================
# Sense
# =========================================================

@router.post(
    "/entries/{entry_id}/senses",
    response_model=VocabularySenseResponse,
)
def create_vocabulary_sense(
    entry_id: int,
    data: VocabularySenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_entry_or_404(
        entry_id,
        db,
    )

    sense = VocabularySense(
        vocabulary_entry_id=entry_id,
        cefr_level=data.cefr_level,
        frequency_rank=data.frequency_rank,
        enrichment_status=(
            data.enrichment_status
        ),
        quality_score=(
            data.quality_score
        ),
        is_active=True,
    )

    db.add(sense)
    db.commit()
    db.refresh(sense)

    return sense


@router.get(
    "/senses/{sense_id}",
    response_model=VocabularySenseResponse,
)
def get_vocabulary_sense(
    sense_id: int,
    db: Session = Depends(get_db),
):
    return get_sense_or_404(
        sense_id,
        db,
    )


# =========================================================
# CEFR assessments
# =========================================================

@router.post(
    "/senses/{sense_id}/cefr-assessments",
    response_model=VocabularyCEFRAssessmentResponse,
)
def create_vocabulary_cefr_assessment(
    sense_id: int,
    data: VocabularyCEFRAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    cefr_level = normalize_level(
        data.cefr_level
    )

    source = data.source.strip().lower()

    if not source:

        raise HTTPException(
            status_code=422,
            detail=(
                "CEFR assessment source "
                "cannot be empty."
            ),
        )

    source_version = (
        clean_optional_text(
            data.source_version
        )
    )

    existing = (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id,
            VocabularyCEFRAssessment
            .cefr_level
            == cefr_level,
            VocabularyCEFRAssessment
            .source
            == source,
            VocabularyCEFRAssessment
            .source_version
            == source_version,
        )
        .first()
    )

    if existing is not None:

        existing.confidence = (
            data.confidence
        )

        if data.is_selected:

            _clear_selected_cefr_assessments(
                sense_id=sense_id,
                db=db,
            )

        existing.is_selected = (
            data.is_selected
        )

        db.commit()
        db.refresh(existing)

        return existing

    if data.is_selected:

        _clear_selected_cefr_assessments(
            sense_id=sense_id,
            db=db,
        )

    assessment = (
        VocabularyCEFRAssessment(
            vocabulary_sense_id=sense_id,
            cefr_level=cefr_level,
            source=source,
            source_version=source_version,
            confidence=data.confidence,
            is_selected=data.is_selected,
        )
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    if data.is_selected:

        sense = get_sense_or_404(
            sense_id,
            db,
        )

        sense.cefr_level = cefr_level

        db.commit()
        db.refresh(assessment)

    return assessment


@router.get(
    "/senses/{sense_id}/cefr-assessments",
    response_model=list[VocabularyCEFRAssessmentResponse],
)
def list_vocabulary_cefr_assessments(
    sense_id: int,
    source: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    db: Session = Depends(get_db),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    query = (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id
        )
    )

    if source:

        query = query.filter(
            VocabularyCEFRAssessment
            .source
            == source.strip().lower()
        )

    return (
        query
        .order_by(
            VocabularyCEFRAssessment
            .is_selected
            .desc(),
            VocabularyCEFRAssessment
            .confidence
            .desc(),
            VocabularyCEFRAssessment
            .id
            .asc(),
        )
        .all()
    )


def _clear_selected_cefr_assessments(
    sense_id: int,
    db: Session,
) -> None:

    (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id,
            VocabularyCEFRAssessment
            .is_selected.is_(True),
        )
        .update(
            {
                VocabularyCEFRAssessment
                .is_selected: False,
            },
            synchronize_session=False,
        )
    )


def _select_cefr_assessment(
    sense_id: int,
    assessment_id: int,
    db: Session,
) -> VocabularySense:

    sense = get_sense_or_404(
        sense_id,
        db,
    )

    assessment = (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment.id
            == assessment_id,
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id,
        )
        .first()
    )

    if assessment is None:

        raise HTTPException(
            status_code=404,
            detail="CEFR assessment not found.",
        )

    _clear_selected_cefr_assessments(
        sense_id=sense_id,
        db=db,
    )

    assessment.is_selected = True

    sense.cefr_level = (
        assessment.cefr_level
    )

    db.commit()
    db.refresh(sense)

    return sense


@router.post(
    "/senses/{sense_id}/cefr-assessments/{assessment_id}/select",
    response_model=VocabularySenseResponse,
)
def select_vocabulary_cefr_assessment(
    sense_id: int,
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    return _select_cefr_assessment(
        sense_id=sense_id,
        assessment_id=assessment_id,
        db=db,
    )


# =========================================================
# Sense localizations
# =========================================================

@router.post(
    "/senses/{sense_id}/localizations",
    response_model=VocabularySenseLocalizationResponse,
)
def create_vocabulary_sense_localization(
    sense_id: int,
    data: VocabularySenseLocalizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    language = normalize_language(
        data.language
    )

    meaning = clean_optional_text(
        data.meaning
    )

    definition = clean_optional_text(
        data.definition
    )

    if (
        meaning is None
        and definition is None
    ):

        raise HTTPException(
            status_code=422,
            detail=(
                "At least one of meaning "
                "or definition must be provided."
            ),
        )

    existing = (
        db.query(
            VocabularySenseLocalization
        )
        .filter(
            VocabularySenseLocalization
            .vocabulary_sense_id
            == sense_id,
            VocabularySenseLocalization
            .language
            == language,
        )
        .first()
    )

    if existing is not None:

        existing.meaning = meaning
        existing.definition = definition

        existing.source = (
            clean_optional_text(
                data.source
            )
        )

        existing.source_version = (
            clean_optional_text(
                data.source_version
            )
        )

        existing.enrichment_status = (
            data.enrichment_status
        )

        existing.quality_score = (
            data.quality_score
        )

        existing.generated_by_ai = (
            data.generated_by_ai
        )

        db.commit()
        db.refresh(existing)

        return existing

    localization = (
        VocabularySenseLocalization(
            vocabulary_sense_id=sense_id,
            language=language,
            meaning=meaning,
            definition=definition,
            source=(
                clean_optional_text(
                    data.source
                )
            ),
            source_version=(
                clean_optional_text(
                    data.source_version
                )
            ),
            enrichment_status=(
                data.enrichment_status
            ),
            quality_score=(
                data.quality_score
            ),
            generated_by_ai=(
                data.generated_by_ai
            ),
        )
    )

    db.add(localization)
    db.commit()
    db.refresh(localization)

    return localization


@router.get(
    "/senses/{sense_id}/localizations",
    response_model=list[VocabularySenseLocalizationResponse],
)
def list_vocabulary_sense_localizations(
    sense_id: int,
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    db: Session = Depends(get_db),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    query = (
        db.query(
            VocabularySenseLocalization
        )
        .filter(
            VocabularySenseLocalization
            .vocabulary_sense_id
            == sense_id
        )
    )

    if language:

        query = query.filter(
            VocabularySenseLocalization
            .language
            == normalize_language(
                language
            )
        )

    return (
        query
        .order_by(
            VocabularySenseLocalization
            .id
            .asc(),
        )
        .all()
    )


# =========================================================
# Translations
# =========================================================

@router.post(
    "/senses/{sense_id}/translations",
    response_model=VocabularyTranslationResponse,
)
def create_vocabulary_translation(
    sense_id: int,
    data: VocabularyTranslationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    language = normalize_language(
        data.language
    )

    translation_text = (
        data.translation.strip()
    )

    if not translation_text:

        raise HTTPException(
            status_code=422,
            detail="Translation cannot be empty.",
        )

    if data.translated_entry_id is not None:

        translated_entry = get_entry_or_404(
            data.translated_entry_id,
            db,
        )

        if (
            translated_entry.language
            != language
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "translated_entry_id must refer "
                    "to an entry in the target language."
                ),
            )

    existing = (
        db.query(
            VocabularyTranslation
        )
        .filter(
            VocabularyTranslation
            .vocabulary_sense_id
            == sense_id,
            VocabularyTranslation
            .language
            == language,
            VocabularyTranslation
            .translation
            == translation_text,
        )
        .first()
    )

    if existing is not None:

        if data.is_primary:

            (
                db.query(
                    VocabularyTranslation
                )
                .filter(
                    VocabularyTranslation
                    .vocabulary_sense_id
                    == sense_id,
                    VocabularyTranslation
                    .language
                    == language,
                    VocabularyTranslation
                    .id
                    != existing.id,
                )
                .update(
                    {
                        VocabularyTranslation
                        .is_primary: False,
                    },
                    synchronize_session=False,
                )
            )

        existing.translated_entry_id = (
            data.translated_entry_id
        )

        existing.is_primary = (
            data.is_primary
        )

        existing.source = (
            clean_optional_text(
                data.source
            )
        )

        existing.source_version = (
            clean_optional_text(
                data.source_version
            )
        )

        existing.generated_by_ai = (
            data.generated_by_ai
        )

        existing.quality_score = (
            data.quality_score
        )

        db.commit()
        db.refresh(existing)

        return existing

    if data.is_primary:

        (
            db.query(
                VocabularyTranslation
            )
            .filter(
                VocabularyTranslation
                .vocabulary_sense_id
                == sense_id,
                VocabularyTranslation
                .language
                == language,
            )
            .update(
                {
                    VocabularyTranslation
                    .is_primary: False,
                },
                synchronize_session=False,
            )
        )

    new_translation = (
        VocabularyTranslation(
            vocabulary_sense_id=sense_id,
            language=language,
            translation=translation_text,
            translated_entry_id=(
                data.translated_entry_id
            ),
            is_primary=data.is_primary,
            source=(
                clean_optional_text(
                    data.source
                )
            ),
            source_version=(
                clean_optional_text(
                    data.source_version
                )
            ),
            generated_by_ai=(
                data.generated_by_ai
            ),
            quality_score=(
                data.quality_score
            ),
        )
    )

    db.add(new_translation)
    db.commit()
    db.refresh(new_translation)

    return new_translation


@router.get(
    "/senses/{sense_id}/translations",
    response_model=list[VocabularyTranslationResponse],
)
def list_vocabulary_translations(
    sense_id: int,
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    db: Session = Depends(get_db),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    query = (
        db.query(
            VocabularyTranslation
        )
        .filter(
            VocabularyTranslation
            .vocabulary_sense_id
            == sense_id
        )
    )

    if language:

        query = query.filter(
            VocabularyTranslation
            .language
            == normalize_language(
                language
            )
        )

    return (
        query
        .order_by(
            VocabularyTranslation
            .is_primary
            .desc(),
            VocabularyTranslation
            .id
            .asc(),
        )
        .all()
    )


# =========================================================
# Examples
# =========================================================

@router.post(
    "/senses/{sense_id}/examples",
    response_model=VocabularyExampleResponse,
)
def create_vocabulary_example(
    sense_id: int,
    data: VocabularyExampleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    sentence = data.sentence.strip()

    if not sentence:

        raise HTTPException(
            status_code=422,
            detail=(
                "Example sentence cannot be empty."
            ),
        )

    example = VocabularyExample(
        vocabulary_sense_id=sense_id,
        sentence=sentence,
        level=(
            normalize_level(data.level)
            if data.level
            else None
        ),
        source=(
            clean_optional_text(
                data.source
            )
        ),
        generated_by_ai=(
            data.generated_by_ai
        ),
        quality_score=(
            data.quality_score
        ),
        is_active=True,
    )

    db.add(example)
    db.commit()
    db.refresh(example)

    return example


@router.get(
    "/examples/{example_id}",
    response_model=VocabularyExampleResponse,
)
def get_vocabulary_example(
    example_id: int,
    db: Session = Depends(get_db),
):
    return get_example_or_404(
        example_id,
        db,
    )


# =========================================================
# Example translations
# =========================================================

@router.post(
    "/examples/{example_id}/translations",
    response_model=VocabularyExampleTranslationResponse,
)
def create_vocabulary_example_translation(
    example_id: int,
    data: VocabularyExampleTranslationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_example_or_404(
        example_id,
        db,
    )

    language = normalize_language(
        data.language
    )

    translation_text = (
        data.translation.strip()
    )

    if not translation_text:

        raise HTTPException(
            status_code=422,
            detail=(
                "Translation cannot be empty."
            ),
        )

    existing = (
        db.query(
            VocabularyExampleTranslation
        )
        .filter(
            VocabularyExampleTranslation
            .vocabulary_example_id
            == example_id,
            VocabularyExampleTranslation
            .language
            == language,
            VocabularyExampleTranslation
            .translation
            == translation_text,
        )
        .first()
    )

    if existing is not None:

        if data.is_primary:

            (
                db.query(
                    VocabularyExampleTranslation
                )
                .filter(
                    VocabularyExampleTranslation
                    .vocabulary_example_id
                    == example_id,
                    VocabularyExampleTranslation
                    .language
                    == language,
                    VocabularyExampleTranslation
                    .id
                    != existing.id,
                )
                .update(
                    {
                        VocabularyExampleTranslation
                        .is_primary: False,
                    },
                    synchronize_session=False,
                )
            )

        existing.is_primary = (
            data.is_primary
        )

        existing.source = (
            clean_optional_text(
                data.source
            )
        )

        existing.source_version = (
            clean_optional_text(
                data.source_version
            )
        )

        existing.generated_by_ai = (
            data.generated_by_ai
        )

        existing.quality_score = (
            data.quality_score
        )

        db.commit()
        db.refresh(existing)

        return existing

    if data.is_primary:

        (
            db.query(
                VocabularyExampleTranslation
            )
            .filter(
                VocabularyExampleTranslation
                .vocabulary_example_id
                == example_id,
                VocabularyExampleTranslation
                .language
                == language,
            )
            .update(
                {
                    VocabularyExampleTranslation
                    .is_primary: False,
                },
                synchronize_session=False,
            )
        )

    new_translation = (
        VocabularyExampleTranslation(
            vocabulary_example_id=example_id,
            language=language,
            translation=translation_text,
            is_primary=data.is_primary,
            source=(
                clean_optional_text(
                    data.source
                )
            ),
            source_version=(
                clean_optional_text(
                    data.source_version
                )
            ),
            generated_by_ai=(
                data.generated_by_ai
            ),
            quality_score=(
                data.quality_score
            ),
        )
    )

    db.add(new_translation)
    db.commit()
    db.refresh(new_translation)

    return new_translation


@router.get(
    "/examples/{example_id}/translations",
    response_model=list[VocabularyExampleTranslationResponse],
)
def list_vocabulary_example_translations(
    example_id: int,
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
    ),
    db: Session = Depends(get_db),
):
    get_example_or_404(
        example_id,
        db,
    )

    query = (
        db.query(
            VocabularyExampleTranslation
        )
        .filter(
            VocabularyExampleTranslation
            .vocabulary_example_id
            == example_id
        )
    )

    if language:

        query = query.filter(
            VocabularyExampleTranslation
            .language
            == normalize_language(
                language
            )
        )

    return (
        query
        .order_by(
            VocabularyExampleTranslation
            .is_primary
            .desc(),
            VocabularyExampleTranslation
            .id
            .asc(),
        )
        .all()
    )


# =========================================================
# Media
# =========================================================

@router.post(
    "/senses/{sense_id}/media",
    response_model=VocabularyMediaResponse,
)
def create_vocabulary_media(
    sense_id: int,
    data: VocabularyMediaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_vocabulary_editor
    ),
):
    get_sense_or_404(
        sense_id,
        db,
    )

    media_type = (
        data.media_type
        .strip()
        .lower()
    )

    url = data.url.strip()

    if not media_type:

        raise HTTPException(
            status_code=422,
            detail="Media type cannot be empty.",
        )

    if not url:

        raise HTTPException(
            status_code=422,
            detail="Media URL cannot be empty.",
        )

    existing = (
        db.query(VocabularyMedia)
        .filter(
            VocabularyMedia.vocabulary_sense_id
            == sense_id,
            VocabularyMedia.media_type
            == media_type,
            VocabularyMedia.url
            == url,
        )
        .first()
    )

    if existing is not None:

        existing.thumbnail_url = (
            clean_optional_text(
                data.thumbnail_url
            )
        )

        existing.alt_text = (
            clean_optional_text(
                data.alt_text
            )
        )

        existing.source = (
            clean_optional_text(
                data.source
            )
        )

        existing.generated_by_ai = (
            data.generated_by_ai
        )

        existing.is_active = True

        db.commit()
        db.refresh(existing)

        return existing

    media = VocabularyMedia(
        vocabulary_sense_id=sense_id,
        media_type=media_type,
        url=url,
        thumbnail_url=(
            clean_optional_text(
                data.thumbnail_url
            )
        ),
        alt_text=(
            clean_optional_text(
                data.alt_text
            )
        ),
        source=(
            clean_optional_text(
                data.source
            )
        ),
        generated_by_ai=(
            data.generated_by_ai
        ),
        is_active=True,
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    return media