from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import (
    PlacementVocabulary,
    VocabularyEntry,
    VocabularySense,
)


# =========================================================
# Supported learning levels
# =========================================================
#
# Placement vocabulary is derived from the main vocabulary
# database.
#
# Order:
#
# PRE_A1 -> A1 -> A2 -> B1 -> B2 -> C1 -> C2
# =========================================================

LEVELS = [
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]


# =========================================================
# Build placement vocabulary from the main vocabulary DB
# =========================================================
#
# The old version of this script imported:
#
# from routers.placement_test import VOCABULARY_BANK
#
# That variable no longer exists in the current project.
#
# Instead of keeping a second vocabulary database, this script
# now derives the placement vocabulary from:
#
# VocabularyEntry
# +
# VocabularySense
#
# This keeps the placement test synchronized with the main
# vocabulary system.
# =========================================================

def get_source_vocabulary(
    db,
) -> dict[str, dict[str, set[str]]]:
    """
    Return vocabulary grouped as:

    {
        "en": {
            "PRE_A1": {"hello", "yes", ...},
            "A1": {"house", "water", ...},
            ...
        },
        "fr": {
            ...
        },
    }

    Only active entries and active senses are used.
    """

    statement = (
        select(
            VocabularyEntry.language,
            VocabularyEntry.word,
            VocabularyEntry.lemma,
            VocabularySense.cefr_level,
        )
        .join(
            VocabularySense,
            VocabularySense.vocabulary_entry_id
            == VocabularyEntry.id,
        )
        .where(
            VocabularyEntry.is_active.is_(True),
            VocabularySense.is_active.is_(True),
            VocabularySense.cefr_level.in_(LEVELS),
        )
    )

    rows = db.execute(statement).all()

    vocabulary: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    for (
        language,
        word,
        lemma,
        level,
    ) in rows:

        if not language:
            continue

        if not level:
            continue

        normalized_language = language.strip().lower()
        normalized_level = level.strip().upper()

        if normalized_level not in LEVELS:
            continue

        # Prefer the displayed word.
        #
        # If it is missing, use lemma.
        source_word = word or lemma

        if source_word is None:
            continue

        source_word = source_word.strip()

        if not source_word:
            continue

        vocabulary[
            normalized_language
        ][
            normalized_level
        ].add(source_word)

    return vocabulary


# =========================================================
# Seed placement vocabulary
# =========================================================

def seed_placement_vocabulary():
    db = SessionLocal()

    try:

        source_vocabulary = get_source_vocabulary(
            db
        )

        inserted_count = 0
        skipped_count = 0

        # Statistics for the final output.
        level_counts: dict[
            str,
            dict[str, int]
        ] = defaultdict(
            lambda: defaultdict(int)
        )

        # -------------------------------------------------
        # Convert the main vocabulary database into
        # placement vocabulary rows.
        # -------------------------------------------------

        for language, levels in source_vocabulary.items():

            for level, words in levels.items():

                for word in sorted(words):

                    normalized_word = word.strip()

                    if not normalized_word:
                        continue

                    statement = (
                        insert(PlacementVocabulary)
                        .values(
                            language=language,
                            level=level,
                            word=normalized_word,
                            is_active=True,
                        )
                        .on_conflict_do_nothing(
                            constraint="uq_placement_vocabulary"
                        )
                    )

                    result = db.execute(
                        statement
                    )

                    if result.rowcount == 1:
                        inserted_count += 1
                        level_counts[
                            language
                        ][
                            level
                        ] += 1

                    else:
                        skipped_count += 1

        db.commit()

        print()
        print("==============================================")
        print("Placement vocabulary seeding completed.")
        print("==============================================")

        if not source_vocabulary:

            print(
                "No active vocabulary with a supported "
                "CEFR level was found."
            )

            print(
                "Import vocabulary data first."
            )

        else:

            for language in sorted(
                source_vocabulary.keys()
            ):

                print()
                print(
                    f"Language: {language}"
                )

                for level in LEVELS:

                    count = len(
                        source_vocabulary[
                            language
                        ].get(
                            level,
                            set()
                        )
                    )

                    inserted_for_level = level_counts[
                        language
                    ].get(
                        level,
                        0
                    )

                    if count == 0:
                        continue

                    print(
                        f"  {level}: "
                        f"{count} source words, "
                        f"{inserted_for_level} inserted"
                    )

        print()
        print("----------------------------------------------")
        print(
            f"Inserted: {inserted_count}"
        )
        print(
            f"Skipped existing: {skipped_count}"
        )
        print("==============================================")
        print()

    except Exception:

        db.rollback()

        print(
            "Placement vocabulary seeding failed."
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_placement_vocabulary()