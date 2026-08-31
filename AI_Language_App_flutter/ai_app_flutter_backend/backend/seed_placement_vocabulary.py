import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import PlacementVocabulary


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


def get_file_vocabulary() -> dict[str, dict[str, set[str]]]:
    """
    Load the placement vocabulary banks exclusively from
    test_vocabulary.json.

    The JSON structure must be:

    {
        "language_code": {
            "PRE_A1": ["word1", "word2", ...],
            "A1": ["word1", "word2", ...],
            ...
        }
    }
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Placement vocabulary file not found: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    result: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )

    if not isinstance(data, dict):
        raise ValueError(
            "test_vocabulary.json must contain a JSON object."
        )

    for language, levels in data.items():
        if not isinstance(levels, dict):
            continue

        language_code = str(language).strip().lower()

        if not language_code:
            continue

        for level, words in levels.items():
            normalized_level = str(level).strip().upper()

            if normalized_level not in LEVELS:
                continue

            if not isinstance(words, list):
                raise ValueError(
                    f"{language_code}/{normalized_level} must be a list of words."
                )

            for word in words:
                if word is None:
                    continue

                value = str(word).strip()

                if value:
                    result[language_code][normalized_level].add(value)

    return result


def seed_placement_vocabulary():
    """
    Seed PlacementVocabulary exclusively from test_vocabulary.json.

    The general vocabulary tables are NOT used.

    Every language/level must contain at least 100 unique words.
    Only the first 100 sorted words are inserted into the placement bank.
    """

    db = SessionLocal()

    try:
        vocabulary = get_file_vocabulary()

        inserted_count = 0
        skipped_count = 0

        incomplete: list[str] = []

        level_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        print()
        print("==============================================")
        print("PLACEMENT VOCABULARY SEEDING")
        print("==============================================")
        print(f"Data file: {DATA_FILE}")
        print("Source: test_vocabulary.json ONLY")
        print()

        for language in sorted(vocabulary):
            print(f"Language: {language}")

            for level in LEVELS:
                words = sorted(
                    vocabulary[language].get(level, set())
                )

                if not words:
                    continue

                print(
                    f"  {level}: {len(words)} words in JSON"
                )

                if len(words) < VOCABULARY_BANK_SIZE:
                    incomplete.append(
                        f"{language}/{level}: "
                        f"{len(words)}/{VOCABULARY_BANK_SIZE}"
                    )
                    continue

                selected_words = words[:VOCABULARY_BANK_SIZE]

                for word in selected_words:
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

        if incomplete:
            db.rollback()

            print()
            print("ERROR: Incomplete placement banks detected.")
            print()

            for item in incomplete:
                print(f"  - {item}")

            print()
            print(
                "Every language/level must contain at least "
                "100 unique words in test_vocabulary.json."
            )

            raise RuntimeError(
                "Placement vocabulary seeding stopped because "
                "one or more banks contain fewer than 100 words."
            )

        db.commit()

        print()
        print("----------------------------------------------")
        print("Placement vocabulary seeding completed.")
        print("----------------------------------------------")
        print(f"Inserted: {inserted_count}")
        print(f"Skipped existing: {skipped_count}")
        print("----------------------------------------------")
        print()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_placement_vocabulary()