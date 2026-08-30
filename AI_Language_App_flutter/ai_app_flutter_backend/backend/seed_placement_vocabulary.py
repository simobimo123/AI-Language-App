import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import (
    PlacementVocabulary,
    VocabularyEntry,
    VocabularySense,
)


LEVELS = [
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

VOCABULARY_BANK_SIZE = 100

DATA_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "placement"
    / "test_vocabulary.json"
)


def get_source_vocabulary(db) -> dict[str, dict[str, set[str]]]:
    statement = (
        select(
            VocabularyEntry.language,
            VocabularyEntry.word,
            VocabularyEntry.lemma,
            VocabularySense.cefr_level,
        )
        .join(
            VocabularySense,
            VocabularySense.vocabulary_entry_id == VocabularyEntry.id,
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

    for language, word, lemma, level in rows:
        if not language or not level:
            continue

        normalized_language = language.strip().lower()
        normalized_level = level.strip().upper()

        if normalized_level not in LEVELS:
            continue

        source_word = word or lemma
        if not source_word:
            continue

        source_word = source_word.strip()
        if source_word:
            vocabulary[normalized_language][normalized_level].add(source_word)

    return vocabulary


def get_file_vocabulary() -> dict[str, dict[str, set[str]]]:
    """Load explicit placement banks used when the main vocabulary DB is incomplete."""
    if not DATA_FILE.exists():
        return {}

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    result: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    if not isinstance(data, dict):
        return result

    for language, levels in data.items():
        if not isinstance(levels, dict):
            continue

        language_code = str(language).strip().lower()
        if not language_code:
            continue

        for level, words in levels.items():
            normalized_level = str(level).strip().upper()
            if normalized_level not in LEVELS or not isinstance(words, list):
                continue

            for word in words:
                if word is None:
                    continue
                value = str(word).strip()
                if value:
                    result[language_code][normalized_level].add(value)

    return result


def merge_vocabulary(
    source: dict[str, dict[str, set[str]]],
    fallback: dict[str, dict[str, set[str]]],
) -> None:
    """Supplement the database vocabulary with explicit placement banks."""
    for language, levels in fallback.items():
        for level, words in levels.items():
            source[language][level].update(words)


def seed_placement_vocabulary():
    db = SessionLocal()

    try:
        source_vocabulary = get_source_vocabulary(db)
        file_vocabulary = get_file_vocabulary()
        merge_vocabulary(source_vocabulary, file_vocabulary)

        inserted_count = 0
        skipped_count = 0
        incomplete: list[str] = []

        level_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        for language, levels in sorted(source_vocabulary.items()):
            for level in LEVELS:
                words = sorted(levels.get(level, set()))
                if not words:
                    continue

                # Placement requires a complete 100-word bank.
                # Do not silently create a smaller bank.
                if len(words) < VOCABULARY_BANK_SIZE:
                    incomplete.append(
                        f"{language}/{level}: {len(words)}/{VOCABULARY_BANK_SIZE}"
                    )
                    continue

                # Keep exactly the first 100 deterministic words in the bank.
                for word in words[:VOCABULARY_BANK_SIZE]:
                    statement = (
                        insert(PlacementVocabulary)
                        .values(
                            language=language,
                            level=level,
                            word=word,
                            is_active=True,
                        )
                        .on_conflict_do_nothing(
                            constraint="uq_placement_vocabulary"
                        )
                    )

                    result = db.execute(statement)
                    if result.rowcount == 1:
                        inserted_count += 1
                        level_counts[language][level] += 1
                    else:
                        skipped_count += 1

        db.commit()

        print()
        print("==============================================")
        print("Placement vocabulary seeding completed.")
        print("==============================================")
        print(f"Data file: {DATA_FILE}")

        for language in sorted(source_vocabulary):
            print(f"\nLanguage: {language}")
            for level in LEVELS:
                count = len(source_vocabulary[language].get(level, set()))
                if count:
                    print(f"  {level}: {count} available")

        if incomplete:
            print("\nIncomplete banks were skipped:")
            for item in incomplete:
                print(f"  - {item}")

        print("\n----------------------------------------------")
        print(f"Inserted: {inserted_count}")
        print(f"Skipped existing: {skipped_count}")
        print("==============================================")
        print()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_placement_vocabulary()
