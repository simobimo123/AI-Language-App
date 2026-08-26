from datetime import datetime

from sqlalchemy.orm import Session

from models import User
from services.ai.context import (
    build_vocabulary_context,
    get_localization,
    get_missing_vocabulary_fields,
    get_translation,
)
from services.ai.enrichment.generator import generate_vocabulary_enrichment
from services.ai.enrichment.persister import (
    get_or_create_entry_and_sense,
    save_cefr_assessment,
    save_forms,
    save_relation,
    upsert_example,
    upsert_localization,
    upsert_translation,
)
from services.ai.normalization import (
    normalize_language,
    normalize_level,
)
from services.ai.schemas import VocabularyEnrichmentResult


def enrich_vocabulary_on_demand(
    word: str,
    current_user: User,
    db: Session,
) -> tuple[
    str | None,
    int,
    int,
    int,
    VocabularyEnrichmentResult | None,
]:

    word = word.strip()

    if not word:

        return (
            None,
            0,
            0,
            0,
            None,
        )

    learning_language = (
        normalize_language(
            current_user.learning_language
        )
    )

    entry, sense = (
        get_or_create_entry_and_sense(
            word=word,
            learning_language=learning_language,
            db=db,
        )
    )

    missing = (
        get_missing_vocabulary_fields(
            entry=entry,
            sense=sense,
            current_user=current_user,
            db=db,
        )
    )

    existing_context = (
        build_vocabulary_context(
            entry=entry,
            sense=sense,
            current_user=current_user,
            db=db,
        )
    )

    if not missing:

        return (
            existing_context,
            0,
            0,
            0,
            VocabularyEnrichmentResult(
                word=word,
                entry_id=entry.id,
                sense_id=sense.id,
                generated=False,
                missing_before=[],
                completed_fields=[],
                remaining_fields=[],
                database_context=(
                    existing_context
                ),
            ),
        )

    (
        enriched,
        prompt_tokens,
        completion_tokens,
        total_tokens,
    ) = generate_vocabulary_enrichment(
        word=word,
        current_user=current_user,
        existing_context=existing_context,
    )

    completed_fields: set[str] = set()

    # -----------------------------------------------------
    # Entry metadata
    # -----------------------------------------------------

    if (
        not entry.part_of_speech
        and enriched.part_of_speech
    ):

        entry.part_of_speech = (
            enriched.part_of_speech.strip()
        )

        completed_fields.add(
            "part_of_speech"
        )

    if (
        not entry.pronunciation
        and enriched.pronunciation
    ):

        entry.pronunciation = (
            enriched.pronunciation.strip()
        )

        completed_fields.add(
            "pronunciation"
        )

    # -----------------------------------------------------
    # Learning localization
    # -----------------------------------------------------

    learning_localization = (
        get_localization(
            sense.id,
            learning_language,
            db,
        )
    )

    if (
        learning_localization is None
        or not learning_localization.meaning
    ):

        if enriched.meaning:

            if upsert_localization(
                sense=sense,
                language=learning_language,
                meaning=enriched.meaning,
                definition=None,
                generated_by_ai=True,
                quality_score=0.8,
                db=db,
            ):

                completed_fields.add(
                    "learning_meaning"
                )

    learning_localization = (
        get_localization(
            sense.id,
            learning_language,
            db,
        )
    )

    if (
        learning_localization is None
        or not learning_localization.definition
    ):

        if enriched.definition:

            if upsert_localization(
                sense=sense,
                language=learning_language,
                meaning=None,
                definition=enriched.definition,
                generated_by_ai=True,
                quality_score=0.8,
                db=db,
            ):

                completed_fields.add(
                    "learning_definition"
                )

    # -----------------------------------------------------
    # Native translation
    # -----------------------------------------------------

    native_language = (
        normalize_language(
            current_user.native_language
        )
    )

    native_translation = get_translation(
        sense.id,
        native_language,
        db,
    )

    if (
        (
            native_translation is None
            or not native_translation.translation
        )
        and enriched.native_translation
    ):

        if upsert_translation(
            sense=sense,
            language=native_language,
            translation=(
                enriched.native_translation
            ),
            generated_by_ai=True,
            quality_score=0.8,
            db=db,
        ):

            completed_fields.add(
                "native_translation"
            )

    # -----------------------------------------------------
    # Native definition
    # -----------------------------------------------------

    existing_native_localization = (
        get_localization(
            sense.id,
            native_language,
            db,
        )
    )

    if (
        (
            existing_native_localization is None
            or not existing_native_localization.definition
        )
        and enriched.native_definition
    ):

        if upsert_localization(
            sense=sense,
            language=native_language,
            meaning=None,
            definition=(
                enriched.native_definition
            ),
            generated_by_ai=True,
            quality_score=0.75,
            db=db,
        ):

            completed_fields.add(
                "native_definition"
            )

    # -----------------------------------------------------
    # CEFR
    # -----------------------------------------------------

    if (
        not sense.cefr_level
        and enriched.cefr_level
    ):

        normalized_cefr = (
            normalize_level(
                enriched.cefr_level
            )
        )

        if normalized_cefr:

            saved = save_cefr_assessment(
                sense=sense,
                level=normalized_cefr,
                confidence=(
                    enriched.cefr_confidence
                ),
                db=db,
            )

            if saved:

                sense.cefr_level = (
                    normalized_cefr
                )

                completed_fields.add(
                    "cefr"
                )

    # -----------------------------------------------------
    # Forms
    # -----------------------------------------------------

    if enriched.forms:

        forms_created = save_forms(
            entry=entry,
            forms=enriched.forms,
            db=db,
        )

        if forms_created > 0:

            completed_fields.add(
                "forms"
            )

    # -----------------------------------------------------
    # Relations
    # -----------------------------------------------------

    relation_count = 0

    for relation in enriched.relations:

        if save_relation(
            source_entry=entry,
            relation_data=relation,
            db=db,
        ):

            relation_count += 1

    if relation_count > 0:

        completed_fields.add(
            "relations"
        )

    # -----------------------------------------------------
    # Example
    # -----------------------------------------------------

    if enriched.example_sentence:

        if upsert_example(
            sense=sense,
            sentence=(
                enriched.example_sentence
            ),
            translations=(
                enriched.example_translations
            ),
            db=db,
        ):

            completed_fields.add(
                "example"
            )

    # -----------------------------------------------------
    # Metadata
    # -----------------------------------------------------

    entry.generated_by_ai = True
    sense.generated_by_ai = True

    # -----------------------------------------------------
    # Completeness
    # -----------------------------------------------------

    missing_after = (
        get_missing_vocabulary_fields(
            entry=entry,
            sense=sense,
            current_user=current_user,
            db=db,
        )
    )

    if missing_after:

        entry.enrichment_status = (
            "partial"
        )

        sense.enrichment_status = (
            "partial"
        )

    else:

        entry.enrichment_status = (
            "complete"
        )

        sense.enrichment_status = (
            "complete"
        )

    if completed_fields:

        now = datetime.utcnow()

        entry.last_enriched_at = now
        sense.last_enriched_at = now
        sense.quality_score = 0.8

    db.commit()

    db.refresh(entry)
    db.refresh(sense)

    database_context = (
        build_vocabulary_context(
            entry=entry,
            sense=sense,
            current_user=current_user,
            db=db,
        )
    )

    result = VocabularyEnrichmentResult(
        word=word,
        entry_id=entry.id,
        sense_id=sense.id,
        generated=True,
        missing_before=sorted(
            missing
        ),
        completed_fields=sorted(
            completed_fields
        ),
        remaining_fields=sorted(
            missing_after
        ),
        database_context=(
            database_context
        ),
    )

    return (
        database_context,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        result,
    )
