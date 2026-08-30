import json
import sys
from pathlib import Path


# =========================================================
# Configuration
# =========================================================

FILE_PATH = Path(
    r"C:\Users\simobimo\Downloads\new\raw-wiktextract-data.jsonl"
)

# كلمات نريد البحث عنها.
# يمكنك تغييرها لاحقًا.
SEARCH_WORDS = {
    "maison",
    "manger",
    "mangeons",
}

# عدد النتائج القصوى لكل كلمة.
MAX_RESULTS_PER_WORD = 3


# =========================================================
# Helpers
# =========================================================

def print_separator():
    print()
    print("=" * 100)
    print()


def compact_value(value, max_chars=3000):
    """
    Convert a JSON value to a readable string without
    printing huge nested structures.
    """

    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )
    except Exception:
        text = repr(value)

    if len(text) > max_chars:
        return (
            text[:max_chars]
            + "\n... [TRUNCATED]"
        )

    return text


def print_entry(entry, line_number):
    print_separator()

    print(
        f"LINE: {line_number}"
    )

    print(
        f"WORD: {entry.get('word')}"
    )

    print(
        f"LANGUAGE: {entry.get('lang')}"
    )

    print(
        f"LANGUAGE CODE: {entry.get('lang_code')}"
    )

    print(
        f"PART OF SPEECH: {entry.get('pos')}"
    )

    print_separator()

    # -----------------------------------------------------
    # Basic fields
    # -----------------------------------------------------

    print("BASIC FIELDS")
    print("-" * 100)

    basic_fields = [
        "word",
        "lang",
        "lang_code",
        "pos",
        "sounds",
        "categories",
        "etymology_text",
    ]

    for field in basic_fields:

        if field in entry:

            print(
                f"\n{field}:"
            )

            print(
                compact_value(
                    entry[field]
                )
            )

    # -----------------------------------------------------
    # Forms
    # -----------------------------------------------------

    print_separator()

    print(
        "FORMS"
    )

    print("-" * 100)

    forms = entry.get(
        "forms"
    )

    if forms:

        print(
            compact_value(
                forms,
                max_chars=8000
            )
        )

    else:

        print(
            "No forms found."
        )

    # -----------------------------------------------------
    # Senses
    # -----------------------------------------------------

    print_separator()

    print(
        "SENSES"
    )

    print("-" * 100)

    senses = entry.get(
        "senses"
    )

    if senses:

        print(
            compact_value(
                senses,
                max_chars=10000
            )
        )

    else:

        print(
            "No senses found."
        )

    # -----------------------------------------------------
    # Translations
    # -----------------------------------------------------

    print_separator()

    print(
        "TRANSLATIONS"
    )

    print("-" * 100)

    translations = entry.get(
        "translations"
    )

    if translations:

        print(
            compact_value(
                translations,
                max_chars=10000
            )
        )

    else:

        print(
            "No translations found."
        )

    # -----------------------------------------------------
    # Lexical relations
    # -----------------------------------------------------

    relation_fields = [
        "synonyms",
        "antonyms",
        "hypernyms",
        "hyponyms",
        "derived",
        "related",
        "holonyms",
        "meronyms",
    ]

    print_separator()

    print(
        "LEXICAL RELATIONS"
    )

    print("-" * 100)

    found_relation = False

    for field in relation_fields:

        if field in entry:

            found_relation = True

            print(
                f"\n{field}:"
            )

            print(
                compact_value(
                    entry[field],
                    max_chars=5000
                )
            )

    if not found_relation:

        print(
            "No common relation fields found."
        )

    print_separator()


# =========================================================
# Main scanner
# =========================================================

def main():

    if not FILE_PATH.exists():

        print(
            "ERROR: File not found:"
        )

        print(
            FILE_PATH
        )

        sys.exit(1)

    if not FILE_PATH.is_file():

        print(
            "ERROR: Path is not a file:"
        )

        print(
            FILE_PATH
        )

        sys.exit(1)

    print(
        "Starting scan..."
    )

    print(
        f"File: {FILE_PATH}"
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "The file will be read line-by-line."
    )

    print(
        "It will NOT be loaded completely into memory."
    )

    print_separator()

    # Track how many matches we found for each word.
    found_counts = {
        word: 0
        for word in SEARCH_WORDS
    }

    total_lines = 0
    invalid_lines = 0

    try:

        with FILE_PATH.open(
            "r",
            encoding="utf-8",
            errors="replace"
        ) as file:

            for line_number, line in enumerate(
                file,
                start=1
            ):

                total_lines += 1

                line = line.strip()

                if not line:
                    continue

                try:

                    entry = json.loads(
                        line
                    )

                except json.JSONDecodeError:

                    invalid_lines += 1

                    continue

                word = entry.get(
                    "word"
                )

                if not isinstance(
                    word,
                    str
                ):

                    continue

                # -------------------------------------------------
                # Exact word matching
                # -------------------------------------------------

                if word in SEARCH_WORDS:

                    if (
                        found_counts[word]
                        < MAX_RESULTS_PER_WORD
                    ):

                        found_counts[word] += 1

                        print_entry(
                            entry,
                            line_number
                        )

                # -------------------------------------------------
                # Stop early when all requested words have enough
                # examples.
                # -------------------------------------------------

                all_complete = all(
                    count >= MAX_RESULTS_PER_WORD
                    for count in found_counts.values()
                )

                if all_complete:

                    break

    except PermissionError:

        print(
            "\nERROR: Windows denied access to the file."
        )

        print(
            "Make sure the file is not locked by another program."
        )

        sys.exit(1)

    except OSError as exc:

        print(
            "\nERROR while reading file:"
        )

        print(
            exc
        )

        sys.exit(1)

    # =====================================================
    # Summary
    # =====================================================

    print_separator()

    print(
        "SCAN COMPLETED"
    )

    print("-" * 100)

    print(
        f"Lines read: {total_lines}"
    )

    print(
        f"Invalid JSON lines: {invalid_lines}"
    )

    print()

    for word, count in found_counts.items():

        print(
            f"{word}: {count} result(s)"
        )

    print_separator()


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    main()