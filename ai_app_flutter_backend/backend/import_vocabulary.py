import csv
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    VocabularyEntry,
    VocabularySense,
    VocabularyExample,
    VocabularyMedia,
)


# =========================================================
# Supported CEFR levels
# =========================================================

CEFR_LEVELS = {
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
}


# =========================================================
# Helpers
# =========================================================

def clean(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def normalize_level(value: Any) -> str | None:
    value = clean(value)

    if value is None:
        return None

    value = value.upper()

    # Handle values such as:
    # A1, a1, CEFR:A1
    if value.startswith("CEFR:"):
        value = value[5:].strip()

    if value not in CEFR_LEVELS:
        return None

    return value


def normalize_language(value: Any) -> str | None:
    value = clean(value)

    if value is None:
        return None

    return value.lower()


# =========================================================
# Supported source fields
# =========================================================
#
# The importer accepts these logical fields.
#
# A source dataset may use different column names.
# The aliases below allow us to map common variations.
# =========================================================

FIELD_ALIASES = {
    "language": [
        "language",
        "lang",
        "language_code",
        "lang_code",
    ],
    "lemma": [
        "lemma",
        "headword",
        "head_word",
        "base_word",
    ],
    "word": [
        "word",
        "term",
        "surface",
    ],
    "part_of_speech": [
        "part_of_speech",
        "pos",
        "partofspeech",
    ],
    "pronunciation": [
        "pronunciation",
        "ipa",
        "phonetic",
    ],
    "frequency_rank": [
        "frequency_rank",
        "frequency",
        "freq_rank",
        "rank",
    ],
    "source": [
        "source",
    ],
    "source_version": [
        "source_version",
        "version",
    ],
    "meaning": [
        "meaning",
        "gloss",
    ],
    "definition": [
        "definition",
        "description",
    ],
    "translation": [
        "translation",
        "translated",
        "meaning_translation",
    ],
    "cefr_level": [
        "cefr_level",
        "cefr",
        "level",
    ],
    "example_sentence": [
        "example_sentence",
        "example",
        "sentence",
        "example_text",
    ],
    "example_translation": [
        "example_translation",
        "example_translated",
        "sentence_translation",
    ],
    "example_level": [
        "example_level",
        "example_cefr",
    ],
    "media_type": [
        "media_type",
        "media",
        "asset_type",
    ],
    "media_url": [
        "media_url",
        "url",
        "image_url",
        "audio_url",
    ],
    "thumbnail_url": [
        "thumbnail_url",
        "thumbnail",
    ],
    "media_alt_text": [
        "media_alt_text",
        "alt_text",
        "alt",
    ],
}


def find_field(
    row: dict[str, Any],
    logical_name: str,
) -> Any:
    aliases = FIELD_ALIASES[logical_name]

    # Build lowercase lookup once.
    lowered = {
        str(key).strip().lower(): value
        for key, value in row.items()
    }

    for alias in aliases:
        if alias in lowered:
            return lowered[alias]

    return None


# =========================================================
# CSV loader
# =========================================================

def load_csv(
    path: Path,
) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        return [
            dict(row)
            for row in reader
        ]


# =========================================================
# JSON loader
# =========================================================

def load_json(
    path: Path,
) -> list[dict[str, Any]]:
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        # Common structure:
        # {
        #   "data": [...]
        # }

        if isinstance(data.get("data"), list):
            return data["data"]

        if isinstance(data.get("items"), list):
            return data["items"]

    raise ValueError(
        "JSON must contain a list of vocabulary records."
    )


# =========================================================
# Load input file
# =========================================================

def load_records(
    path: Path,
) -> list[dict[str, Any]]:

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return load_csv(path)

    if suffix == ".json":
        return load_json(path)

    raise ValueError(
        "Only CSV and JSON files are supported."
    )


# =========================================================
# Find or create VocabularyEntry
# =========================================================

def get_or_create_entry(
    row: dict[str, Any],
    db: Session,
) -> VocabularyEntry:

    language = normalize_language(
        find_field(row, "language")
    )

    lemma = clean(
        find_field(row, "lemma")
    )

    word = clean(
        find_field(row, "word")
    )

    part_of_speech = clean(
        find_field(row, "part_of_speech")
    )

    if language is None:
        raise ValueError(
            "Missing language."
        )

    if lemma is None:
        # If lemma is unavailable, use the word itself.
        lemma = word

    if lemma is None:
        raise ValueError(
            "Missing lemma/word."
        )

    # -----------------------------------------------------
    # Search existing entry.
    #
    # We explicitly search rather than relying only on the
    # database unique constraint because PostgreSQL treats
    # NULL values specially in unique constraints.
    # -----------------------------------------------------

    statement = (
        select(VocabularyEntry)
        .where(
            VocabularyEntry.language == language,
            VocabularyEntry.lemma == lemma,
            VocabularyEntry.part_of_speech
            == part_of_speech,
        )
    )

    entry = db.execute(
        statement
    ).scalar_one_or_none()

    if entry is not None:

        # Update missing information when new data provides it.

        if word is not None:
            entry.word = word

        pronunciation = clean(
            find_field(row, "pronunciation")
        )

        if pronunciation is not None:
            entry.pronunciation = pronunciation

        frequency_value = clean(
            find_field(row, "frequency_rank")
        )

        if frequency_value is not None:
            try:
                entry.frequency_rank = int(
                    float(frequency_value)
                )
            except ValueError:
                pass

        source = clean(
            find_field(row, "source")
        )

        if source is not None:
            entry.source = source

        source_version = clean(
            find_field(row, "source_version")
        )

        if source_version is not None:
            entry.source_version = source_version

        return entry

    # -----------------------------------------------------
    # Create new entry.
    # -----------------------------------------------------

    entry = VocabularyEntry(
        language=language,
        lemma=lemma,
        word=word,
        part_of_speech=part_of_speech,
        pronunciation=clean(
            find_field(row, "pronunciation")
        ),
        source=clean(
            find_field(row, "source")
        ),
        source_version=clean(
            find_field(row, "source_version")
        ),
        is_active=True,
    )

    frequency_value = clean(
        find_field(row, "frequency_rank")
    )

    if frequency_value is not None:
        try:
            entry.frequency_rank = int(
                float(frequency_value)
            )
        except ValueError:
            pass

    db.add(entry)
    db.flush()

    return entry


# =========================================================
# Find or create sense
# =========================================================

def get_or_create_sense(
    row: dict[str, Any],
    entry: VocabularyEntry,
    db: Session,
) -> VocabularySense | None:

    meaning = clean(
        find_field(row, "meaning")
    )

    definition = clean(
        find_field(row, "definition")
    )

    translation = clean(
        find_field(row, "translation")
    )

    cefr_level = normalize_level(
        find_field(row, "cefr_level")
    )

    # If there is absolutely no sense information,
    # there is nothing to create.
    if (
        meaning is None
        and definition is None
        and translation is None
        and cefr_level is None
    ):
        return None

    # -----------------------------------------------------
    # Search an existing equivalent sense.
    # -----------------------------------------------------

    statement = (
        select(VocabularySense)
        .where(
            VocabularySense.vocabulary_entry_id
            == entry.id,
            VocabularySense.meaning
            == meaning,
            VocabularySense.definition
            == definition,
            VocabularySense.translation
            == translation,
            VocabularySense.cefr_level
            == cefr_level,
        )
    )

    sense = db.execute(
        statement
    ).scalar_one_or_none()

    if sense is not None:
        return sense

    sense = VocabularySense(
        vocabulary_entry_id=entry.id,
        meaning=meaning,
        definition=definition,
        translation=translation,
        cefr_level=cefr_level,
        is_active=True,
    )

    frequency_value = clean(
        find_field(row, "frequency_rank")
    )

    if frequency_value is not None:
        try:
            sense.frequency_rank = int(
                float(frequency_value)
            )
        except ValueError:
            pass

    db.add(sense)
    db.flush()

    return sense


# =========================================================
# Add example
# =========================================================

def add_example(
    row: dict[str, Any],
    sense: VocabularySense | None,
    db: Session,
) -> None:

    if sense is None:
        return

    sentence = clean(
        find_field(row, "example_sentence")
    )

    if sentence is None:
        return

    translation = clean(
        find_field(row, "example_translation")
    )

    level = normalize_level(
        find_field(row, "example_level")
    )

    # Avoid importing the same example repeatedly.

    statement = (
        select(VocabularyExample)
        .where(
            VocabularyExample.vocabulary_sense_id
            == sense.id,
            VocabularyExample.sentence
            == sentence,
            VocabularyExample.translation
            == translation,
        )
    )

    existing = db.execute(
        statement
    ).scalar_one_or_none()

    if existing is not None:
        return

    example = VocabularyExample(
        vocabulary_sense_id=sense.id,
        sentence=sentence,
        translation=translation,
        level=level,
        source=clean(
            find_field(row, "source")
        ),
        is_active=True,
    )

    db.add(example)


# =========================================================
# Add media
# =========================================================

def add_media(
    row: dict[str, Any],
    sense: VocabularySense | None,
    db: Session,
) -> None:

    if sense is None:
        return

    media_url = clean(
        find_field(row, "media_url")
    )

    if media_url is None:
        return

    media_type = clean(
        find_field(row, "media_type")
    )

    if media_type is None:
        media_type = "image"

    thumbnail_url = clean(
        find_field(row, "thumbnail_url")
    )

    alt_text = clean(
        find_field(row, "media_alt_text")
    )

    statement = (
        select(VocabularyMedia)
        .where(
            VocabularyMedia.vocabulary_sense_id
            == sense.id,
            VocabularyMedia.media_type
            == media_type,
            VocabularyMedia.url
            == media_url,
        )
    )

    existing = db.execute(
        statement
    ).scalar_one_or_none()

    if existing is not None:
        return

    media = VocabularyMedia(
        vocabulary_sense_id=sense.id,
        media_type=media_type,
        url=media_url,
        thumbnail_url=thumbnail_url,
        alt_text=alt_text,
        source=clean(
            find_field(row, "source")
        ),
        is_active=True,
    )

    db.add(media)


# =========================================================
# Import records
# =========================================================

def import_records(
    records: list[dict[str, Any]],
    db: Session,
) -> None:

    entries_created = 0
    entries_existing = 0

    senses_created = 0
    examples_created = 0
    media_created = 0

    skipped = 0

    for index, row in enumerate(
        records,
        start=1,
    ):

        try:

            before_entry_id = None

            entry = get_or_create_entry(
                row=row,
                db=db,
            )

            before_entry_id = entry.id

            if entry.id is not None:
                entries_existing += 1

            sense = get_or_create_sense(
                row=row,
                entry=entry,
                db=db,
            )

            if sense is not None:
                senses_created += 1

            add_example(
                row=row,
                sense=sense,
                db=db,
            )

            add_media(
                row=row,
                sense=sense,
                db=db,
            )

            if index % 500 == 0:
                db.commit()

                print(
                    f"Processed {index}/{len(records)} records..."
                )

        except Exception as exc:

            skipped += 1

            print(
                f"Skipped record #{index}: {exc}"
            )

    db.commit()

    print()
    print("==============================================")
    print("Vocabulary import completed.")
    print("==============================================")
    print(
        f"Records processed: {len(records)}"
    )
    print(
        f"Skipped: {skipped}"
    )
    print(
        f"Senses processed: {senses_created}"
    )
    print("==============================================")


# =========================================================
# Main
# =========================================================

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python import_vocabulary.py "
            "path/to/file.csv"
        )

        print(
            "or"
        )

        print(
            "python import_vocabulary.py "
            "path/to/file.json"
        )

        raise SystemExit(1)

    file_path = Path(
        sys.argv[1]
    )

    if not file_path.exists():

        print(
            f"File not found: {file_path}"
        )

        raise SystemExit(1)

    records = load_records(
        file_path
    )

    print(
        f"Loaded {len(records)} records."
    )

    db = SessionLocal()

    try:

        import_records(
            records=records,
            db=db,
        )

    except Exception:

        db.rollback()

        print(
            "Vocabulary import failed."
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()