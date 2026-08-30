import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models import (
    VocabularyCEFRAssessment,
    VocabularyEntry,
    VocabularyExample,
    VocabularyExampleTranslation,
    VocabularyForm,
    VocabularyRelation,
    VocabularySense,
    VocabularySenseLocalization,
    VocabularyTranslation,
)
from services.ai.client import AI_MODEL
from services.ai.context import (
    find_vocabulary_entry,
    get_localization,
    get_senses,
)
from services.ai.normalization import (
    normalize_confidence,
    normalize_language,
    normalize_level,
    normalize_text,
)
from services.ai.schemas import (
    AIExampleTranslation,
    AIVocabularyForm,
    AIVocabularyRelation,
)


logger = logging.getLogger(__name__)


VOCABULARY_AI_SOURCE = "ai"
VOCABULARY_AI_SOURCE_VERSION = AI_MODEL


def find_best_sense(
    entry: VocabularyEntry,
    learning_language: str,
    db: Session,
) -> VocabularySense | None:

    senses = get_senses(
        entry.id,
        db,
    )

    if not senses:
        return None

    for sense in senses:

        localization = get_localization(
            sense.id,
            learning_language,
            db,
        )

        if localization is not None:
            return sense

    return senses[0]


def get_or_create_entry_and_sense(
    word: str,
    learning_language: str,
    db: Session,
) -> tuple[
    VocabularyEntry,
    VocabularySense,
]:

    entry = find_vocabulary_entry(
        word=word,
        language=learning_language,
        db=db,
    )

    if entry is None:

        normalized = (
            normalize_text(
                word
            )
            or word.strip().casefold()
        )

        entry = VocabularyEntry(
            language=learning_language,
            lemma=word.strip(),
            normalized_lemma=normalized,
            word=word.strip(),
            part_of_speech=None,
            pronunciation=None,
            frequency_rank=None,
            source=VOCABULARY_AI_SOURCE,
            source_version=(
                VOCABULARY_AI_SOURCE_VERSION
            ),
            enrichment_status="partial",
            quality_score=None,
            generated_by_ai=True,
            last_enriched_at=None,
            is_active=True,
        )

        db.add(entry)
        db.flush()

    sense = find_best_sense(
        entry=entry,
        learning_language=learning_language,
        db=db,
    )

    if sense is None:

        sense = VocabularySense(
            vocabulary_entry_id=entry.id,
            meaning=None,
            definition=None,
            cefr_level=None,
            frequency_rank=None,
            enrichment_status="partial",
            quality_score=None,
            generated_by_ai=True,
            last_enriched_at=None,
            is_active=True,
        )

        db.add(sense)
        db.flush()

    return (
        entry,
        sense,
    )


# =========================================================
# Save localization
# =========================================================

def upsert_localization(
    sense: VocabularySense,
    language: str,
    meaning: str | None,
    definition: str | None,
    generated_by_ai: bool,
    quality_score: float | None,
    db: Session,
) -> bool:

    meaning = (
        meaning.strip()
        if meaning
        else None
    )

    definition = (
        definition.strip()
        if definition
        else None
    )

    if not meaning and not definition:
        return False

    existing = get_localization(
        sense.id,
        language,
        db,
    )

    if existing is None:

        existing = (
            VocabularySenseLocalization(
                vocabulary_sense_id=sense.id,
                language=language,
                meaning=meaning,
                definition=definition,
                source=VOCABULARY_AI_SOURCE,
                source_version=(
                    VOCABULARY_AI_SOURCE_VERSION
                ),
                enrichment_status="complete",
                quality_score=quality_score,
                generated_by_ai=generated_by_ai,
            )
        )

        db.add(existing)
        db.flush()

        return True

    changed = False

    if meaning and not existing.meaning:

        existing.meaning = meaning
        changed = True

    if definition and not existing.definition:

        existing.definition = definition
        changed = True

    if (
        generated_by_ai
        and not existing.generated_by_ai
    ):

        existing.generated_by_ai = True
        changed = True

    if (
        quality_score is not None
        and existing.quality_score
        != quality_score
    ):

        existing.quality_score = (
            quality_score
        )
        changed = True

    if changed:

        existing.source = (
            VOCABULARY_AI_SOURCE
        )

        existing.source_version = (
            VOCABULARY_AI_SOURCE_VERSION
        )

        existing.enrichment_status = (
            "complete"
        )

    return changed


# =========================================================
# Save translation
# =========================================================

def upsert_translation(
    sense: VocabularySense,
    language: str,
    translation: str | None,
    generated_by_ai: bool,
    quality_score: float | None,
    db: Session,
) -> bool:

    if not translation:
        return False

    translation = (
        translation.strip()
    )

    if not translation:
        return False

    existing = db.execute(
        select(
            VocabularyTranslation
        )
        .where(
            VocabularyTranslation
            .vocabulary_sense_id
            == sense.id,
            VocabularyTranslation
            .language
            == language,
            VocabularyTranslation
            .translation
            == translation,
        )
    ).scalar_one_or_none()

    if existing is not None:

        changed = False

        if (
            generated_by_ai
            and not existing.generated_by_ai
        ):

            existing.generated_by_ai = True
            changed = True

        if (
            quality_score is not None
            and existing.quality_score
            != quality_score
        ):

            existing.quality_score = (
                quality_score
            )
            changed = True

        return changed

    current_translations = (
        db.execute(
            select(
                VocabularyTranslation
            )
            .where(
                VocabularyTranslation
                .vocabulary_sense_id
                == sense.id,
                VocabularyTranslation
                .language
                == language,
            )
        )
        .scalars()
        .all()
    )

    is_primary = not bool(
        current_translations
    )

    db.add(
        VocabularyTranslation(
            vocabulary_sense_id=sense.id,
            language=language,
            translation=translation,
            translated_entry_id=None,
            is_primary=is_primary,
            source=VOCABULARY_AI_SOURCE,
            source_version=(
                VOCABULARY_AI_SOURCE_VERSION
            ),
            generated_by_ai=generated_by_ai,
            quality_score=quality_score,
        )
    )

    db.flush()

    return True


# =========================================================
# Save example
# =========================================================

def upsert_example(
    sense: VocabularySense,
    sentence: str | None,
    translations: list[
        AIExampleTranslation
    ],
    db: Session,
) -> bool:

    if not sentence:
        return False

    sentence = sentence.strip()

    if not sentence:
        return False

    existing = db.execute(
        select(
            VocabularyExample
        )
        .where(
            VocabularyExample
            .vocabulary_sense_id
            == sense.id,
            VocabularyExample
            .sentence
            == sentence,
        )
    ).scalar_one_or_none()

    if existing is None:

        existing = VocabularyExample(
            vocabulary_sense_id=sense.id,
            sentence=sentence,
            level=None,
            source=VOCABULARY_AI_SOURCE,
            generated_by_ai=True,
            quality_score=None,
            is_active=True,
        )

        db.add(existing)
        db.flush()

        created = True

    else:

        existing.generated_by_ai = True

        if not existing.source:
            existing.source = (
                VOCABULARY_AI_SOURCE
            )

        created = False

    for translation_data in translations:

        try:

            language = normalize_language(
                translation_data.language
            )

        except ValueError:

            logger.warning(
                "Skipping unsupported example "
                "translation language: %s",
                translation_data.language,
            )

            continue

        translation = (
            translation_data.translation.strip()
        )

        if not translation:
            continue

        duplicate = db.execute(
            select(
                VocabularyExampleTranslation
            )
            .where(
                VocabularyExampleTranslation
                .vocabulary_example_id
                == existing.id,
                VocabularyExampleTranslation
                .language
                == language,
                VocabularyExampleTranslation
                .translation
                == translation,
            )
        ).scalar_one_or_none()

        if duplicate is not None:
            continue

        primary_exists = db.execute(
            select(
                VocabularyExampleTranslation
            )
            .where(
                VocabularyExampleTranslation
                .vocabulary_example_id
                == existing.id,
                VocabularyExampleTranslation
                .language
                == language,
                VocabularyExampleTranslation
                .is_primary.is_(True),
            )
        ).scalar_one_or_none()

        db.add(
            VocabularyExampleTranslation(
                vocabulary_example_id=(
                    existing.id
                ),
                language=language,
                translation=translation,
                is_primary=(
                    primary_exists is None
                ),
                source=VOCABULARY_AI_SOURCE,
                source_version=(
                    VOCABULARY_AI_SOURCE_VERSION
                ),
                generated_by_ai=True,
                quality_score=None,
            )
        )

    db.flush()

    return created


# =========================================================
# Save forms
# =========================================================

def save_forms(
    entry: VocabularyEntry,
    forms: list[
        AIVocabularyForm
    ],
    db: Session,
) -> int:

    created_count = 0

    for item in forms:

        form_value = (
            item.form.strip()
        )

        if not form_value:
            continue

        normalized = (
            form_value
            .casefold()
            .strip()
        )

        existing = db.execute(
            select(
                VocabularyForm
            )
            .where(
                VocabularyForm
                .vocabulary_entry_id
                == entry.id,
                VocabularyForm
                .form
                == form_value,
            )
        ).scalar_one_or_none()

        if existing is not None:

            existing.source = (
                VOCABULARY_AI_SOURCE
            )

            existing.source_version = (
                VOCABULARY_AI_SOURCE_VERSION
            )

            if item.form_type:

                existing.form_type = (
                    item.form_type.strip()
                )

            if item.grammatical_features:

                existing.grammatical_features = (
                    item.grammatical_features
                )

            if item.is_lemma:

                existing.is_lemma = True

            continue

        db.add(
            VocabularyForm(
                vocabulary_entry_id=entry.id,
                form=form_value,
                normalized_form=normalized,
                grammatical_features=(
                    item.grammatical_features
                ),
                form_type=(
                    item.form_type.strip()
                    if item.form_type
                    else None
                ),
                is_lemma=item.is_lemma,
                source=VOCABULARY_AI_SOURCE,
                source_version=(
                    VOCABULARY_AI_SOURCE_VERSION
                ),
                is_active=True,
            )
        )

        created_count += 1

    if created_count:
        db.flush()

    return created_count


# =========================================================
# Save CEFR
# =========================================================

def save_cefr_assessment(
    sense: VocabularySense,
    level: str | None,
    confidence,
    db: Session,
) -> bool:

    normalized_level = (
        normalize_level(
            level
        )
    )

    if normalized_level is None:
        return False

    confidence = (
        normalize_confidence(
            confidence
        )
    )

    existing = db.execute(
        select(
            VocabularyCEFRAssessment
        )
        .where(
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense.id,
            VocabularyCEFRAssessment
            .cefr_level
            == normalized_level,
            VocabularyCEFRAssessment
            .source
            == VOCABULARY_AI_SOURCE,
            VocabularyCEFRAssessment
            .source_version
            == VOCABULARY_AI_SOURCE_VERSION,
        )
    ).scalar_one_or_none()

    if existing is None:

        db.add(
            VocabularyCEFRAssessment(
                vocabulary_sense_id=sense.id,
                cefr_level=normalized_level,
                source=VOCABULARY_AI_SOURCE,
                source_version=(
                    VOCABULARY_AI_SOURCE_VERSION
                ),
                confidence=confidence,
                is_selected=False,
            )
        )

        db.flush()

        return True

    if confidence > existing.confidence:

        existing.confidence = (
            confidence
        )

    return False


# =========================================================
# Save relation
# =========================================================

def save_relation(
    source_entry: VocabularyEntry,
    relation_data: AIVocabularyRelation,
    db: Session,
) -> bool:

    target_word = (
        relation_data.word.strip()
    )

    if not target_word:
        return False

    normalized_target = (
        target_word
        .casefold()
        .strip()
    )

    target_entry = (
        db.execute(
            select(
                VocabularyEntry
            )
            .where(
                VocabularyEntry.language
                == source_entry.language,
                VocabularyEntry.is_active.is_(True),
                or_(
                    VocabularyEntry
                    .normalized_lemma
                    == normalized_target,
                    func.lower(
                        VocabularyEntry
                        .lemma
                    )
                    == normalized_target,
                    func.lower(
                        VocabularyEntry
                        .word
                    )
                    == normalized_target,
                ),
            )
            .order_by(
                VocabularyEntry.id.asc()
            )
        )
        .scalars()
        .first()
    )

    if target_entry is None:
        return False

    if target_entry.id == source_entry.id:
        return False

    existing = db.execute(
        select(
            VocabularyRelation
        )
        .where(
            VocabularyRelation
            .source_entry_id
            == source_entry.id,
            VocabularyRelation
            .target_entry_id
            == target_entry.id,
            VocabularyRelation
            .relation_type
            == relation_data.relation_type,
        )
    ).scalar_one_or_none()

    if existing is not None:
        return False

    db.add(
        VocabularyRelation(
            source_entry_id=source_entry.id,
            target_entry_id=target_entry.id,
            source_sense_id=None,
            target_sense_id=None,
            relation_type=(
                relation_data.relation_type
            ),
            language=source_entry.language,
            is_bidirectional=(
                relation_data.relation_type
                in {
                    "synonym",
                    "antonym",
                    "related",
                }
            ),
            is_active=True,
            source=VOCABULARY_AI_SOURCE,
            source_version=(
                VOCABULARY_AI_SOURCE_VERSION
            ),
        )
    )

    db.flush()

    return True
