import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
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


# =========================================================
# Supported application languages
# =========================================================
#
# هذه هي اللغات التي سيدعمها التطبيق في قاعدة المفردات.
#
# أي لغة أخرى موجودة في Wiktextract سيتم تجاهلها أثناء
# الاستيراد.
# =========================================================

SUPPORTED_LANGUAGES = {
    "ar",  # Arabic
    "de",  # German
    "en",  # English
    "es",  # Spanish
    "fa",  # Persian
    "fr",  # French
    "hi",  # Hindi
    "id",  # Indonesian
    "it",  # Italian
    "ja",  # Japanese
    "ko",  # Korean
    "nl",  # Dutch
    "pl",  # Polish
    "pt",  # Portuguese
    "ru",  # Russian
    "th",  # Thai
    "tr",  # Turkish
    "uk",  # Ukrainian
    "vi",  # Vietnamese
    "zh",  # Chinese
}


LANGUAGE_CODE_ALIASES = {
    # Chinese
    "cmn": "zh",
    "cmn-hans": "zh",
    "cmn-hant": "zh",
    "yue": "zh",
    "zh-hans": "zh",
    "zh-hant": "zh",
    "nan-hbl": "zh",

    # Persian
    "fa-ira": "fa",
    "fa-afg": "fa",

    # Portuguese
    "pt-br": "pt",
    "pt-pt": "pt",

    # Arabic
    "arb": "ar",
    "ara": "ar",

    # Indonesian
    "ind": "id",

    # Japanese
    "jpn": "ja",

    # Korean
    "kor": "ko",

    # Vietnamese
    "vie": "vi",

    # Thai
    "tha": "th",

    # Hindi
    "hin": "hi",

    # Turkish
    "tur": "tr",

    # Ukrainian
    "ukr": "uk",

    # Russian
    "rus": "ru",

    # German
    "deu": "de",

    # French
    "fra": "fr",

    # Italian
    "ita": "it",

    # Spanish
    "spa": "es",

    # Polish
    "pol": "pl",

    # Dutch
    "nld": "nl",

    # Portuguese
    "por": "pt",

    # English
    "eng": "en",
}


# =========================================================
# Supported CEFR levels
# =========================================================

CEFR_LEVELS = {
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
}


# =========================================================
# Import metadata
# =========================================================

WIKTEXTRACT_SOURCE = "wiktextract"
WIKTEXTRACT_SOURCE_VERSION = "raw-wiktextract-data"


# =========================================================
# Import performance
# =========================================================

COMMIT_EVERY = 2500


# =========================================================
# Relation types
# =========================================================

RELATION_FIELDS = {
    "synonyms": "synonym",
    "antonyms": "antonym",
    "derived": "derived",
    "related": "related",
    "hypernyms": "hypernym",
    "hyponyms": "hyponym",
    "holonyms": "holonym",
    "meronyms": "meronym",
    "coordinate_terms": "coordinate_term",
    "see_also": "see_also",
}


# =========================================================
# Runtime caches
# =========================================================
#
# الهدف الأساسي:
# تقليل استعلامات PostgreSQL المتكررة أثناء الاستيراد
# الضخم.
#
# بعض البيانات مثل الترجمة أو form أو relation لا تحتاج
# إلى إعادة التحقق من قاعدة البيانات بعد أول مرة.
# =========================================================

entry_cache: dict[
    tuple[str, str, str | None],
    VocabularyEntry,
] = {}

relation_target_cache: dict[
    tuple[str, str, str | None],
    VocabularyEntry,
] = {}

sense_cache: dict[
    tuple[int, str | None, str, str],
    VocabularySense,
] = {}

# Cache for all candidate senses of:
# (entry_id, cefr_level)
sense_candidates_cache: dict[
    tuple[int, str | None],
    list[VocabularySense],
] = {}

# Cache normalized localization contents:
# (sense_id, language) -> (normalized_meaning, normalized_definition)
sense_localization_cache: dict[
    tuple[int, str],
    tuple[str, str],
] = {}

localization_cache: set[
    tuple[int, str]
] = set()

translation_cache: set[
    tuple[int, str, str]
] = set()

example_cache: dict[
    tuple[int, str],
    VocabularyExample,
] = {}

example_translation_cache: set[
    tuple[int, str, str]
] = set()

media_cache: set[
    tuple[int, str, str]
] = set()

form_cache: set[
    tuple[int, str]
] = set()

relation_cache: set[
    tuple[int, int, str]
] = set()

cefr_assessment_cache: set[
    tuple[int, str, str, str | None]
] = set()


# =========================================================
# Counters for cache statistics
# =========================================================

cache_stats = {
    "entry_hits": 0,
    "entry_misses": 0,
    "relation_target_hits": 0,
    "relation_target_misses": 0,
    "sense_hits": 0,
    "sense_misses": 0,
    "localization_hits": 0,
    "translation_hits": 0,
    "form_hits": 0,
    "relation_hits": 0,
    "example_hits": 0,
    "media_hits": 0,
}


# =========================================================
# Helpers
# =========================================================

def clean(
    value: Any,
) -> str | None:

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


def normalize_level(
    value: Any,
) -> str | None:

    value = clean(value)

    if value is None:
        return None

    value = value.upper()

    if value.startswith("CEFR:"):
        value = value[5:].strip()

    value = value.replace("-", "_")

    if value not in CEFR_LEVELS:
        return None

    return value


def normalize_language(
    value: Any,
) -> str | None:

    value = clean(value)

    if value is None:
        return None

    value = value.lower()

    value = LANGUAGE_CODE_ALIASES.get(
        value,
        value,
    )

    if value not in SUPPORTED_LANGUAGES:
        return None

    return value


def normalize_list(
    value: Any,
) -> list[dict[str, Any]]:

    if value is None:
        return []

    if isinstance(value, list):

        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

    return []


def normalize_glosses(
    value: Any,
) -> list[str]:

    if not isinstance(value, list):
        return []

    result = []

    for item in value:

        text = clean(item)

        if text is not None:
            result.append(text)

    return result


def normalize_text_for_matching(
    value: Any,
) -> str:

    text = clean(value)

    if text is None:
        return ""

    text = text.casefold()

    text = text.replace(
        "&",
        " and ",
    )

    # Remove parenthetical content.
    text = re.sub(
        r"\([^)]*\)",
        " ",
        text,
    )

    # Keep Unicode letters/numbers from all languages.
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def glosses_match(
    left: Any,
    right: Any,
) -> bool:

    left_normalized = (
        normalize_text_for_matching(left)
    )

    right_normalized = (
        normalize_text_for_matching(right)
    )

    if (
        not left_normalized
        or not right_normalized
    ):
        return False

    if left_normalized == right_normalized:
        return True

    if (
        left_normalized in right_normalized
        or right_normalized in left_normalized
    ):
        return True

    left_words = set(
        left_normalized.split()
    )

    right_words = set(
        right_normalized.split()
    )

    if (
        not left_words
        or not right_words
    ):
        return False

    intersection = (
        left_words & right_words
    )

    smaller = min(
        len(left_words),
        len(right_words),
    )

    if smaller <= 2:
        return len(intersection) == smaller

    overlap = (
        len(intersection) / smaller
    )

    return overlap >= 0.75


# =========================================================
# CSV aliases
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
    "meaning_language": [
        "meaning_language",
        "meaning_lang",
    ],
    "definition_language": [
        "definition_language",
        "definition_lang",
    ],
    "translation": [
        "translation",
        "translated",
        "meaning_translation",
    ],
    "translation_language": [
        "translation_language",
        "translation_lang",
        "target_language",
        "target_lang",
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
    "example_language": [
        "example_language",
        "example_lang",
    ],
    "example_translation": [
        "example_translation",
        "example_translated",
        "sentence_translation",
    ],
    "example_translation_language": [
        "example_translation_language",
        "example_translation_lang",
        "example_target_language",
        "example_target_lang",
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

    lowered = {
        str(key).strip().lower(): value
        for key, value in row.items()
    }

    for alias in aliases:

        if alias in lowered:
            return lowered[alias]

    return None


# =========================================================
# Loaders
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


def load_json(
    path: Path,
) -> list[dict[str, Any]]:

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        if isinstance(
            data.get("data"),
            list,
        ):
            return data["data"]

        if isinstance(
            data.get("items"),
            list,
        ):
            return data["items"]

    raise ValueError(
        "JSON must contain a list of vocabulary records."
    )


# =========================================================
# Wiktextract pronunciation
# =========================================================

def extract_wiktextract_pronunciation(
    row: dict[str, Any],
) -> str | None:

    sounds = normalize_list(
        row.get("sounds")
    )

    for sound in sounds:

        ipa = clean(
            sound.get("ipa")
        )

        if ipa is not None:
            return ipa

    return None


# =========================================================
# Wiktextract media
# =========================================================

def extract_wiktextract_media(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    sounds = normalize_list(
        row.get("sounds")
    )

    media = []

    for sound in sounds:

        mp3_url = clean(
            sound.get("mp3_url")
        )

        ogg_url = clean(
            sound.get("ogg_url")
        )

        audio_url = (
            mp3_url
            or ogg_url
        )

        if audio_url is None:
            continue

        media.append(
            {
                "media_type": "audio",
                "url": audio_url,
                "thumbnail_url": None,
                "alt_text": None,
                "source": WIKTEXTRACT_SOURCE,
            }
        )

    unique_media = []

    seen_urls = set()

    for item in media:

        url = item["url"]

        if url in seen_urls:
            continue

        seen_urls.add(url)

        unique_media.append(item)

    return unique_media


# =========================================================
# Wiktextract examples
# =========================================================

def extract_wiktextract_examples(
    sense_data: dict[str, Any],
) -> list[dict[str, Any]]:

    raw_examples = normalize_list(
        sense_data.get("examples")
    )

    examples = []

    seen_sentences = set()

    for example in raw_examples:

        sentence = clean(
            example.get("text")
        )

        if sentence is None:
            continue

        normalized_sentence = (
            normalize_text_for_matching(
                sentence
            )
        )

        if (
            normalized_sentence
            in seen_sentences
        ):
            continue

        seen_sentences.add(
            normalized_sentence
        )

        examples.append(
            {
                "sentence": sentence,
                "level": None,
                "source": WIKTEXTRACT_SOURCE,
                "translations": [],
            }
        )

    return examples


# =========================================================
# Translation sense matching
# =========================================================

def translation_belongs_to_sense(
    translation: dict[str, Any],
    glosses: list[str],
) -> bool:

    translation_sense = clean(
        translation.get("sense")
    )

    if translation_sense is None:
        return True

    if not glosses:
        return True

    for gloss in glosses:

        if glosses_match(
            translation_sense,
            gloss,
        ):
            return True

    return False


# =========================================================
# Wiktextract translations
# =========================================================

def extract_wiktextract_translations(
    row: dict[str, Any],
    glosses: list[str],
    source_language: str,
) -> list[dict[str, Any]]:

    translations = normalize_list(
        row.get("translations")
    )

    result = []

    seen = set()

    primary_languages = set()

    for translation in translations:

        if not translation_belongs_to_sense(
            translation,
            glosses,
        ):
            continue

        raw_language = (
            translation.get("lang_code")
            or translation.get("code")
        )

        language = normalize_language(
            raw_language
        )

        if language is None:
            continue

        word = clean(
            translation.get("word")
        )

        if word is None:
            continue

        if language == source_language:
            continue

        key = (
            language,
            normalize_text_for_matching(
                word
            ),
        )

        if key in seen:
            continue

        seen.add(key)

        is_primary = (
            language
            not in primary_languages
        )

        if is_primary:
            primary_languages.add(
                language
            )

        result.append(
            {
                "language": language,
                "translation": word,
                "is_primary": is_primary,
                "source": WIKTEXTRACT_SOURCE,
            }
        )

    return result


# =========================================================
# Wiktextract forms
# =========================================================

def extract_wiktextract_forms(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    forms = normalize_list(
        row.get("forms")
    )

    result = []

    seen = set()

    for form_data in forms:

        form = clean(
            form_data.get("form")
        )

        if form is None:
            continue

        normalized = (
            normalize_text_for_matching(
                form
            )
        )

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)

        tags = form_data.get(
            "tags",
            [],
        )

        if not isinstance(
            tags,
            list,
        ):
            tags = []

        cleaned_tags = [
            clean(tag)
            for tag in tags
            if clean(tag) is not None
        ]

        grammatical_features = {
            "tags": cleaned_tags,
        }

        source = clean(
            form_data.get("source")
        )

        if source is None:
            source = WIKTEXTRACT_SOURCE

        result.append(
            {
                "form": form,
                "grammatical_features": (
                    grammatical_features
                ),
                "source": source,
                "source_version": (
                    WIKTEXTRACT_SOURCE_VERSION
                ),
            }
        )

    return result


# =========================================================
# Wiktextract relations
# =========================================================

def extract_wiktextract_relations(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    result = []

    seen = set()

    source_language = normalize_language(
        row.get("lang_code")
    )

    if source_language is None:
        return result

    for (
        field_name,
        relation_type,
    ) in RELATION_FIELDS.items():

        relation_items = normalize_list(
            row.get(field_name)
        )

        for relation_item in relation_items:

            target_word = clean(
                relation_item.get("word")
            )

            if target_word is None:
                continue

            raw_target_language = (
                relation_item.get(
                    "lang_code"
                )
                or relation_item.get(
                    "language"
                )
                or source_language
            )

            target_language = normalize_language(
                raw_target_language
            )

            if target_language is None:
                continue

            target_pos = clean(
                relation_item.get("pos")
            )

            key = (
                relation_type,
                target_language,
                normalize_text_for_matching(
                    target_word
                ),
                target_pos,
            )

            if key in seen:
                continue

            seen.add(key)

            result.append(
                {
                    "relation_type": relation_type,
                    "language": target_language,
                    "word": target_word,
                    "part_of_speech": target_pos,
                    "sense": clean(
                        relation_item.get(
                            "sense"
                        )
                    ),
                    "source": WIKTEXTRACT_SOURCE,
                    "source_version": (
                        WIKTEXTRACT_SOURCE_VERSION
                    ),
                }
            )

    return result


# =========================================================
# Convert Wiktextract record
# =========================================================

def convert_wiktextract_record(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    source_language = normalize_language(
        row.get("lang_code")
    )

    if source_language is None:
        return []

    word = clean(
        row.get("word")
    )

    if word is None:
        return []

    pos = clean(
        row.get("pos")
    )

    senses = normalize_list(
        row.get("senses")
    )

    if not senses:
        return []

    pronunciation = (
        extract_wiktextract_pronunciation(
            row
        )
    )

    media = extract_wiktextract_media(
        row
    )

    forms = extract_wiktextract_forms(
        row
    )

    relations = extract_wiktextract_relations(
        row
    )

    converted = []

    for (
        sense_index,
        sense_data,
    ) in enumerate(
        senses,
        start=1,
    ):

        glosses = normalize_glosses(
            sense_data.get("glosses")
        )

        if not glosses:

            glosses = normalize_glosses(
                sense_data.get(
                    "raw_glosses"
                )
            )

        if not glosses:
            continue

        meaning = glosses[0]

        definition = "; ".join(
            glosses
        )

        localizations = [
            {
                "language": source_language,
                "meaning": meaning,
                "definition": definition,
                "source": WIKTEXTRACT_SOURCE,
                "source_version": (
                    WIKTEXTRACT_SOURCE_VERSION
                ),
            }
        ]

        translations = (
            extract_wiktextract_translations(
                row=row,
                glosses=glosses,
                source_language=source_language,
            )
        )

        examples = (
            extract_wiktextract_examples(
                sense_data
            )
        )

        converted_record = {
            "language": source_language,
            "lemma": word,
            "word": word,
            "part_of_speech": pos,
            "pronunciation": pronunciation,
            "frequency_rank": None,
            "source": WIKTEXTRACT_SOURCE,
            "source_version": (
                WIKTEXTRACT_SOURCE_VERSION
            ),
            "cefr_level": None,
            "cefr_assessments": [],
            "localizations": localizations,
            "translations": translations,
            "examples": examples,
            "media": media,
            "forms": forms,
            "relations": relations,
            "_wiktextract_sense_index": (
                sense_index
            ),
        }

        converted.append(
            converted_record
        )

    return converted


# =========================================================
# JSONL iterator
# =========================================================

def iter_wiktextract_records(
    path: Path,
) -> Iterator[dict[str, Any]]:

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        for (
            line_number,
            line,
        ) in enumerate(
            file,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:

                row = json.loads(
                    line
                )

            except json.JSONDecodeError as exc:

                print(
                    f"Skipping invalid JSONL line "
                    f"#{line_number}: {exc}"
                )

                continue

            if not isinstance(
                row,
                dict,
            ):
                continue

            converted_records = (
                convert_wiktextract_record(
                    row
                )
            )

            for record in converted_records:
                yield record


# =========================================================
# Unified iterator
# =========================================================

def iter_records(
    path: Path,
) -> Iterator[dict[str, Any]]:

    suffix = path.suffix.lower()

    if suffix == ".jsonl":

        yield from iter_wiktextract_records(
            path
        )

        return

    if suffix == ".csv":

        for record in load_csv(path):
            yield record

        return

    if suffix == ".json":

        for record in load_json(path):
            yield record

        return

    raise ValueError(
        "Supported files are CSV, JSON and JSONL."
    )


# =========================================================
# Vocabulary Entry
# =========================================================

def get_or_create_entry(
    row: dict[str, Any],
    db: Session,
) -> VocabularyEntry:

    language = normalize_language(
        row.get("language")
        if "language" in row
        else find_field(
            row,
            "language",
        )
    )

    if language is None:
        raise ValueError(
            "Unsupported or missing vocabulary language."
        )

    lemma = clean(
        row.get("lemma")
        if "lemma" in row
        else find_field(
            row,
            "lemma",
        )
    )

    word = clean(
        row.get("word")
        if "word" in row
        else find_field(
            row,
            "word",
        )
    )

    part_of_speech = clean(
        row.get("part_of_speech")
        if "part_of_speech" in row
        else find_field(
            row,
            "part_of_speech",
        )
    )

    if lemma is None:
        lemma = word

    if lemma is None:
        raise ValueError(
            "Missing lemma/word."
        )

    cache_key = (
        language,
        lemma,
        part_of_speech,
    )

    cached = entry_cache.get(
        cache_key
    )

    if cached is not None:

        cache_stats["entry_hits"] += 1

        # Update only fields that may differ between
        # duplicate Wiktextract records.
        pronunciation = clean(
            row.get("pronunciation")
            if "pronunciation" in row
            else find_field(
                row,
                "pronunciation",
            )
        )

        if pronunciation is not None:
            cached.pronunciation = pronunciation

        return cached

    cache_stats["entry_misses"] += 1

    # -----------------------------------------------------
    # IMPORTANT PERFORMANCE OPTIMIZATION
    #
    # no_autoflush prevents unrelated pending INSERTs from
    # being flushed before every lookup query.
    # -----------------------------------------------------

    with db.no_autoflush:

        statement = (
            select(VocabularyEntry)
            .where(
                VocabularyEntry.language
                == language,
                VocabularyEntry.lemma
                == lemma,
                VocabularyEntry.part_of_speech
                == part_of_speech,
            )
        )

        entry = db.execute(
            statement
        ).scalar_one_or_none()

    pronunciation = clean(
        row.get("pronunciation")
        if "pronunciation" in row
        else find_field(
            row,
            "pronunciation",
        )
    )

    frequency_value = clean(
        row.get("frequency_rank")
        if "frequency_rank" in row
        else find_field(
            row,
            "frequency_rank",
        )
    )

    frequency_rank = None

    if frequency_value is not None:

        try:

            frequency_rank = int(
                float(
                    frequency_value
                )
            )

        except ValueError:
            pass

    source = clean(
        row.get("source")
        if "source" in row
        else find_field(
            row,
            "source",
        )
    )

    source_version = clean(
        row.get("source_version")
        if "source_version" in row
        else find_field(
            row,
            "source_version",
        )
    )

    if entry is not None:

        if word is not None:
            entry.word = word

        if pronunciation is not None:
            entry.pronunciation = pronunciation

        if frequency_rank is not None:
            entry.frequency_rank = (
                frequency_rank
            )

        if source is not None:
            entry.source = source

        if source_version is not None:
            entry.source_version = (
                source_version
            )

        entry_cache[cache_key] = entry

        return entry

    entry = VocabularyEntry(
        language=language,
        lemma=lemma,
        word=word,
        part_of_speech=part_of_speech,
        pronunciation=pronunciation,
        frequency_rank=frequency_rank,
        source=source,
        source_version=source_version,
        is_active=True,
    )

    db.add(entry)

    # We need the ID immediately because child tables depend
    # on this entry.
    db.flush()

    entry_cache[cache_key] = entry

    return entry


# =========================================================
# Related / target Entry
# =========================================================

def get_or_create_relation_target_entry(
    source_entry: VocabularyEntry,
    relation: dict[str, Any],
    db: Session,
) -> VocabularyEntry | None:

    target_word = clean(
        relation.get("word")
    )

    if target_word is None:
        return None

    target_language = normalize_language(
        relation.get("language")
    )

    if target_language is None:
        return None

    target_pos = clean(
        relation.get("part_of_speech")
    )

    relation_type = clean(
        relation.get("relation_type")
    )

    if relation_type is None:
        return None

    if (
        target_pos is None
        and relation_type in {
            "synonym",
            "antonym",
            "related",
            "hypernym",
            "hyponym",
            "holonym",
            "meronym",
            "coordinate_term",
            "see_also",
        }
        and target_language
        == source_entry.language
    ):
        target_pos = (
            source_entry.part_of_speech
        )

    cache_key = (
        target_language,
        target_word,
        target_pos,
    )

    cached = relation_target_cache.get(
        cache_key
    )

    if cached is not None:

        cache_stats[
            "relation_target_hits"
        ] += 1

        return cached

    # Entry cache can often resolve the same target
    # without another DB query.
    cached_entry = entry_cache.get(
        cache_key
    )

    if cached_entry is not None:

        cache_stats[
            "relation_target_hits"
        ] += 1

        relation_target_cache[
            cache_key
        ] = cached_entry

        return cached_entry

    cache_stats[
        "relation_target_misses"
    ] += 1

    # -----------------------------------------------------
    # Exact POS match
    # -----------------------------------------------------

    if target_pos is not None:

        exact_statement = (
            select(VocabularyEntry)
            .where(
                VocabularyEntry.language
                == target_language,
                VocabularyEntry.lemma
                == target_word,
                VocabularyEntry.part_of_speech
                == target_pos,
            )
        )

        with db.no_autoflush:

            exact_entry = db.execute(
                exact_statement
            ).scalar_one_or_none()

        if exact_entry is not None:

            relation_target_cache[
                cache_key
            ] = exact_entry

            entry_cache[
                cache_key
            ] = exact_entry

            return exact_entry

    # -----------------------------------------------------
    # Same language + lemma fallback
    # -----------------------------------------------------

    any_statement = (
        select(VocabularyEntry)
        .where(
            VocabularyEntry.language
            == target_language,
            VocabularyEntry.lemma
            == target_word,
        )
        .order_by(
            VocabularyEntry.id.asc()
        )
    )

    with db.no_autoflush:

        existing_entries = db.execute(
            any_statement
        ).scalars().all()

    if existing_entries:

        selected_entry = (
            existing_entries[0]
        )

        if target_pos is not None:

            for existing_entry in existing_entries:

                if (
                    existing_entry.part_of_speech
                    == target_pos
                ):

                    selected_entry = (
                        existing_entry
                    )

                    break

        relation_target_cache[
            cache_key
        ] = selected_entry

        entry_cache[
            (
                target_language,
                target_word,
                selected_entry.part_of_speech,
            )
        ] = selected_entry

        return selected_entry

    # -----------------------------------------------------
    # Create lightweight target entry
    # -----------------------------------------------------

    target_entry = VocabularyEntry(
        language=target_language,
        lemma=target_word,
        word=target_word,
        part_of_speech=target_pos,
        pronunciation=None,
        frequency_rank=None,
        source=WIKTEXTRACT_SOURCE,
        source_version=(
            WIKTEXTRACT_SOURCE_VERSION
        ),
        is_active=True,
    )

    db.add(target_entry)
    db.flush()

    relation_target_cache[
        cache_key
    ] = target_entry

    entry_cache[
        cache_key
    ] = target_entry

    return target_entry


# =========================================================
# Add Vocabulary Relation
# =========================================================

def add_vocabulary_relation(
    source_entry: VocabularyEntry,
    relation: dict[str, Any],
    db: Session,
) -> bool:

    relation_type = clean(
        relation.get("relation_type")
    )

    if relation_type is None:
        return False

    target_entry = (
        get_or_create_relation_target_entry(
            source_entry=source_entry,
            relation=relation,
            db=db,
        )
    )

    if target_entry is None:
        return False

    if target_entry.id == source_entry.id:
        return False

    cache_key = (
        source_entry.id,
        target_entry.id,
        relation_type,
    )

    if cache_key in relation_cache:

        cache_stats["relation_hits"] += 1

        return False

    with db.no_autoflush:

        existing = db.query(
            VocabularyRelation
        ).filter(
            VocabularyRelation.source_entry_id
            == source_entry.id,
            VocabularyRelation.target_entry_id
            == target_entry.id,
            VocabularyRelation.relation_type
            == relation_type,
        ).first()

    if existing is not None:

        relation_cache.add(
            cache_key
        )

        return False

    db.add(
        VocabularyRelation(
            source_entry_id=source_entry.id,
            target_entry_id=target_entry.id,
            relation_type=relation_type,
            language=source_entry.language,
            is_active=True,
        )
    )

    relation_cache.add(
        cache_key
    )

    return True


# =========================================================
# Add Vocabulary Form
# =========================================================

def add_vocabulary_form(
    entry: VocabularyEntry,
    form_data: dict[str, Any],
    db: Session,
) -> bool:

    form = clean(
        form_data.get("form")
    )

    if form is None:
        return False

    normalized_form = (
        normalize_text_for_matching(
            form
        )
    )

    if not normalized_form:
        return False

    cache_key = (
        entry.id,
        normalized_form,
    )

    if cache_key in form_cache:

        cache_stats["form_hits"] += 1

        return False

    grammatical_features = (
        form_data.get(
            "grammatical_features"
        )
    )

    if not isinstance(
        grammatical_features,
        dict,
    ):
        grammatical_features = {}

    source = clean(
        form_data.get("source")
    )

    source_version = clean(
        form_data.get(
            "source_version"
        )
    )

    with db.no_autoflush:

        existing = db.query(
            VocabularyForm
        ).filter(
            VocabularyForm.vocabulary_entry_id
            == entry.id,
            VocabularyForm.form
            == form,
        ).first()

    if existing is not None:

        existing.normalized_form = (
            normalized_form
        )

        existing.grammatical_features = (
            grammatical_features
        )

        if source is not None:
            existing.source = source

        if source_version is not None:
            existing.source_version = (
                source_version
            )

        form_cache.add(
            cache_key
        )

        return False

    db.add(
        VocabularyForm(
            vocabulary_entry_id=entry.id,
            form=form,
            normalized_form=normalized_form,
            grammatical_features=(
                grammatical_features
            ),
            source=source,
            source_version=source_version,
            is_active=True,
        )
    )

    form_cache.add(
        cache_key
    )

    return True


# =========================================================
# Build localizations
# =========================================================

def get_localization_records(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    localizations = normalize_list(
        row.get("localizations")
    )

    if localizations:
        return localizations

    meaning = clean(
        find_field(
            row,
            "meaning",
        )
    )

    definition = clean(
        find_field(
            row,
            "definition",
        )
    )

    if (
        meaning is None
        and definition is None
    ):
        return []

    language = normalize_language(
        find_field(
            row,
            "meaning_language",
        )
    )

    definition_language = normalize_language(
        find_field(
            row,
            "definition_language",
        )
    )

    language = (
        language
        or definition_language
        or normalize_language(
            row.get("language")
        )
    )

    if language is None:
        raise ValueError(
            "A localization language is required."
        )

    return [
        {
            "language": language,
            "meaning": meaning,
            "definition": definition,
            "source": clean(
                find_field(
                    row,
                    "source",
                )
            ),
            "source_version": clean(
                find_field(
                    row,
                    "source_version",
                )
            ),
        }
    ]


# =========================================================
# Find or create Sense
# =========================================================

def get_or_create_sense(
    row: dict[str, Any],
    entry: VocabularyEntry,
    db: Session,
) -> VocabularySense | None:

    cefr_level = normalize_level(
        row.get("cefr_level")
        if "cefr_level" in row
        else find_field(
            row,
            "cefr_level",
        )
    )

    localizations = (
        get_localization_records(
            row
        )
    )

    if (
        cefr_level is None
        and not localizations
    ):
        return None

    source_language_localization = None

    for localization in localizations:

        localization_language = (
            normalize_language(
                localization.get(
                    "language"
                )
            )
        )

        if (
            localization_language
            == entry.language
        ):

            source_language_localization = (
                localization
            )

            break

    if (
        source_language_localization
        is None
        and localizations
    ):
        source_language_localization = (
            localizations[0]
        )

    source_meaning = (
        clean(
            source_language_localization.get(
                "meaning"
            )
        )
        if source_language_localization
        else None
    )

    source_definition = (
        clean(
            source_language_localization.get(
                "definition"
            )
        )
        if source_language_localization
        else None
    )

    normalized_meaning = (
        normalize_text_for_matching(
            source_meaning
        )
    )

    normalized_definition = (
        normalize_text_for_matching(
            source_definition
        )
    )

    cache_key = (
        entry.id,
        cefr_level,
        normalized_meaning,
        normalized_definition,
    )

    cached = sense_cache.get(
        cache_key
    )

    if cached is not None:

        cache_stats["sense_hits"] += 1

        return cached

    cache_stats["sense_misses"] += 1

    candidate_cache_key = (
        entry.id,
        cefr_level,
    )

    candidate_senses = (
        sense_candidates_cache.get(
            candidate_cache_key
        )
    )

    if candidate_senses is None:

        # IMPORTANT:
        # Do not flush every pending INSERT before this lookup.
        with db.no_autoflush:

            candidate_senses = db.query(
                VocabularySense
            ).filter(
                VocabularySense.vocabulary_entry_id
                == entry.id,
                VocabularySense.cefr_level
                == cefr_level,
                VocabularySense.is_active.is_(
                    True
                ),
            ).all()

        sense_candidates_cache[
            candidate_cache_key
        ] = candidate_senses

    for candidate in candidate_senses:

        localization_key = (
            candidate.id,
            entry.language,
        )

        cached_localization = (
            sense_localization_cache.get(
                localization_key
            )
        )

        if cached_localization is None:

            with db.no_autoflush:

                localization = db.query(
                    VocabularySenseLocalization
                ).filter(
                    VocabularySenseLocalization
                    .vocabulary_sense_id
                    == candidate.id,
                    VocabularySenseLocalization
                    .language
                    == entry.language,
                ).first()

            if localization is None:

                cached_localization = (
                    "",
                    "",
                )

            else:

                cached_localization = (
                    normalize_text_for_matching(
                        localization.meaning
                    ),
                    normalize_text_for_matching(
                        localization.definition
                    ),
                )

            sense_localization_cache[
                localization_key
            ] = cached_localization

        candidate_meaning, candidate_definition = (
            cached_localization
        )

        if (
            candidate_meaning
            == normalized_meaning
            and candidate_definition
            == normalized_definition
        ):

            sense_cache[
                cache_key
            ] = candidate

            return candidate

    # -----------------------------------------------------
    # Legacy fallback
    # -----------------------------------------------------

    if len(candidate_senses) == 1:

        candidate = candidate_senses[0]

        localization_key = (
            candidate.id,
            entry.language,
        )

        cached_localization = (
            sense_localization_cache.get(
                localization_key
            )
        )

        if cached_localization is None:

            with db.no_autoflush:

                localization_count = db.query(
                    VocabularySenseLocalization
                ).filter(
                    VocabularySenseLocalization
                    .vocabulary_sense_id
                    == candidate.id
                ).count()

            if localization_count == 0:

                sense_cache[
                    cache_key
                ] = candidate

                return candidate

        elif cached_localization == ("", ""):

            sense_cache[
                cache_key
            ] = candidate

            return candidate

    # -----------------------------------------------------
    # Create new sense
    # -----------------------------------------------------

    frequency_value = clean(
        row.get("frequency_rank")
        if "frequency_rank" in row
        else find_field(
            row,
            "frequency_rank",
        )
    )

    frequency_rank = None

    if frequency_value is not None:

        try:

            frequency_rank = int(
                float(
                    frequency_value
                )
            )

        except ValueError:
            pass

    sense = VocabularySense(
        vocabulary_entry_id=entry.id,
        meaning=None,
        definition=None,
        cefr_level=cefr_level,
        frequency_rank=frequency_rank,
        is_active=True,
    )

    db.add(sense)
    db.flush()

    # Update candidate cache immediately so a later sense
    # with the same entry/level sees the new sense.
    sense_candidates_cache.setdefault(
        candidate_cache_key,
        [],
    ).append(sense)

    sense_cache[
        cache_key
    ] = sense

    return sense


# =========================================================
# Localization
# =========================================================

def upsert_localization(
    sense: VocabularySense,
    localization: dict[str, Any],
    db: Session,
) -> bool:

    language = normalize_language(
        localization.get("language")
    )

    if language is None:
        return False

    cache_key = (
        sense.id,
        language,
    )

    meaning = clean(
        localization.get("meaning")
    )

    definition = clean(
        localization.get("definition")
    )

    if (
        meaning is None
        and definition is None
    ):
        return False

    source = clean(
        localization.get("source")
    )

    source_version = clean(
        localization.get(
            "source_version"
        )
    )

    if cache_key in localization_cache:

        cache_stats[
            "localization_hits"
        ] += 1

        return False

    with db.no_autoflush:

        existing = db.query(
            VocabularySenseLocalization
        ).filter(
            VocabularySenseLocalization
            .vocabulary_sense_id
            == sense.id,
            VocabularySenseLocalization
            .language
            == language,
        ).first()

    if existing is not None:

        existing.meaning = meaning
        existing.definition = definition
        existing.source = source
        existing.source_version = (
            source_version
        )

        localization_cache.add(
            cache_key
        )

        sense_localization_cache[
            cache_key
        ] = (
            normalize_text_for_matching(
                meaning
            ),
            normalize_text_for_matching(
                definition
            ),
        )

        return False

    db.add(
        VocabularySenseLocalization(
            vocabulary_sense_id=sense.id,
            language=language,
            meaning=meaning,
            definition=definition,
            source=source,
            source_version=source_version,
        )
    )

    localization_cache.add(
        cache_key
    )

    sense_localization_cache[
        cache_key
    ] = (
        normalize_text_for_matching(
            meaning
        ),
        normalize_text_for_matching(
            definition
        ),
    )

    return True


# =========================================================
# Translation
# =========================================================

def add_translation(
    sense: VocabularySense,
    translation: dict[str, Any],
    db: Session,
) -> bool:

    language = normalize_language(
        translation.get("language")
    )

    if language is None:
        return False

    translation_text = clean(
        translation.get(
            "translation"
        )
    )

    if translation_text is None:
        return False

    normalized_translation = (
        normalize_text_for_matching(
            translation_text
        )
    )

    cache_key = (
        sense.id,
        language,
        normalized_translation,
    )

    source = clean(
        translation.get("source")
    )

    is_primary = bool(
        translation.get(
            "is_primary",
            False,
        )
    )

    if cache_key in translation_cache:

        cache_stats[
            "translation_hits"
        ] += 1

        return False

    with db.no_autoflush:

        existing = db.query(
            VocabularyTranslation
        ).filter(
            VocabularyTranslation
            .vocabulary_sense_id
            == sense.id,
            VocabularyTranslation.language
            == language,
            VocabularyTranslation.translation
            == translation_text,
        ).first()

    if existing is not None:

        if is_primary:
            existing.is_primary = True

        if source is not None:
            existing.source = source

        translation_cache.add(
            cache_key
        )

        return False

    if not is_primary:

        with db.no_autoflush:

            existing_primary = db.query(
                VocabularyTranslation
            ).filter(
                VocabularyTranslation
                .vocabulary_sense_id
                == sense.id,
                VocabularyTranslation.language
                == language,
                VocabularyTranslation
                .is_primary.is_(True),
            ).first()

        is_primary = (
            existing_primary is None
        )

    db.add(
        VocabularyTranslation(
            vocabulary_sense_id=sense.id,
            language=language,
            translation=translation_text,
            is_primary=is_primary,
            source=source,
        )
    )

    translation_cache.add(
        cache_key
    )

    return True


# =========================================================
# Examples
# =========================================================

def add_example(
    sense: VocabularySense,
    example_data: dict[str, Any],
    db: Session,
) -> tuple[
    VocabularyExample,
    bool,
    int,
] | None:

    sentence = clean(
        example_data.get("sentence")
    )

    if sentence is None:
        return None

    normalized_sentence = (
        normalize_text_for_matching(
            sentence
        )
    )

    if not normalized_sentence:
        return None

    cache_key = (
        sense.id,
        normalized_sentence,
    )

    level = normalize_level(
        example_data.get("level")
    )

    source = clean(
        example_data.get("source")
    )

    existing = example_cache.get(
        cache_key
    )

    created = False

    if existing is not None:

        cache_stats["example_hits"] += 1

        example = existing

    else:

        with db.no_autoflush:

            example = db.query(
                VocabularyExample
            ).filter(
                VocabularyExample
                .vocabulary_sense_id
                == sense.id,
                VocabularyExample.sentence
                == sentence,
            ).first()

        if example is not None:

            example_cache[
                cache_key
            ] = example

        else:

            example = VocabularyExample(
                vocabulary_sense_id=sense.id,
                sentence=sentence,
                level=level,
                source=source,
                is_active=True,
            )

            db.add(example)
            db.flush()

            example_cache[
                cache_key
            ] = example

            created = True

    if not created:

        if level is not None:
            example.level = level

        if source is not None:
            example.source = source

    translation_count = 0

    translations = normalize_list(
        example_data.get(
            "translations"
        )
    )

    for translation in translations:

        language = normalize_language(
            translation.get("language")
        )

        translation_text = clean(
            translation.get(
                "translation"
            )
        )

        if (
            language is None
            or translation_text is None
        ):
            continue

        normalized_translation = (
            normalize_text_for_matching(
                translation_text
            )
        )

        translation_cache_key = (
            example.id,
            language,
            normalized_translation,
        )

        source_translation = clean(
            translation.get("source")
        )

        is_primary = bool(
            translation.get(
                "is_primary",
                False,
            )
        )

        if (
            translation_cache_key
            in example_translation_cache
        ):
            continue

        with db.no_autoflush:

            existing_translation = (
                db.query(
                    VocabularyExampleTranslation
                )
                .filter(
                    VocabularyExampleTranslation
                    .vocabulary_example_id
                    == example.id,
                    VocabularyExampleTranslation
                    .language
                    == language,
                    VocabularyExampleTranslation
                    .translation
                    == translation_text,
                )
                .first()
            )

        if (
            existing_translation
            is not None
        ):

            if is_primary:
                existing_translation.is_primary = True

            if source_translation is not None:
                existing_translation.source = (
                    source_translation
                )

            example_translation_cache.add(
                translation_cache_key
            )

            continue

        if not is_primary:

            with db.no_autoflush:

                existing_primary = (
                    db.query(
                        VocabularyExampleTranslation
                    )
                    .filter(
                        VocabularyExampleTranslation
                        .vocabulary_example_id
                        == example.id,
                        VocabularyExampleTranslation
                        .language
                        == language,
                        VocabularyExampleTranslation
                        .is_primary.is_(True),
                    )
                    .first()
                )

            is_primary = (
                existing_primary is None
            )

        db.add(
            VocabularyExampleTranslation(
                vocabulary_example_id=(
                    example.id
                ),
                language=language,
                translation=(
                    translation_text
                ),
                is_primary=is_primary,
                source=source_translation,
            )
        )

        example_translation_cache.add(
            translation_cache_key
        )

        translation_count += 1

    return (
        example,
        created,
        translation_count,
    )


# =========================================================
# Media
# =========================================================

def add_media(
    sense: VocabularySense,
    media_data: dict[str, Any],
    db: Session,
) -> bool:

    media_url = clean(
        media_data.get("url")
        or media_data.get(
            "media_url"
        )
    )

    if media_url is None:
        return False

    media_type = clean(
        media_data.get("media_type")
    )

    if media_type is None:
        media_type = "image"

    media_type = media_type.lower()

    cache_key = (
        sense.id,
        media_type,
        media_url,
    )

    if cache_key in media_cache:

        cache_stats["media_hits"] += 1

        return False

    thumbnail_url = clean(
        media_data.get(
            "thumbnail_url"
        )
    )

    alt_text = clean(
        media_data.get("alt_text")
        or media_data.get(
            "media_alt_text"
        )
    )

    source = clean(
        media_data.get("source")
    )

    with db.no_autoflush:

        existing = db.query(
            VocabularyMedia
        ).filter(
            VocabularyMedia
            .vocabulary_sense_id
            == sense.id,
            VocabularyMedia.media_type
            == media_type,
            VocabularyMedia.url
            == media_url,
        ).first()

    if existing is not None:

        media_cache.add(
            cache_key
        )

        return False

    db.add(
        VocabularyMedia(
            vocabulary_sense_id=sense.id,
            media_type=media_type,
            url=media_url,
            thumbnail_url=thumbnail_url,
            alt_text=alt_text,
            source=source,
            is_active=True,
        )
    )

    media_cache.add(
        cache_key
    )

    return True


# =========================================================
# CEFR Assessments
# =========================================================

def add_cefr_assessments(
    row: dict[str, Any],
    sense: VocabularySense,
    db: Session,
) -> int:

    assessments = normalize_list(
        row.get("cefr_assessments")
    )

    if not assessments:

        cefr_level = normalize_level(
            row.get("cefr_level")
        )

        source = clean(
            row.get("source")
        )

        source_version = clean(
            row.get(
                "source_version"
            )
        )

        if cefr_level is not None:

            if source is None:
                source = "dataset"

            assessments = [
                {
                    "cefr_level": cefr_level,
                    "source": source,
                    "source_version": (
                        source_version
                    ),
                    "confidence": 1.0,
                    "selected": True,
                }
            ]

    created_or_updated = 0

    for assessment in assessments:

        cefr_level = normalize_level(
            assessment.get(
                "cefr_level"
            )
        )

        source = clean(
            assessment.get(
                "source"
            )
        )

        if (
            cefr_level is None
            or source is None
        ):
            continue

        source = source.lower()

        source_version = clean(
            assessment.get(
                "source_version"
            )
        )

        cache_key = (
            sense.id,
            cefr_level,
            source,
            source_version,
        )

        confidence = assessment.get(
            "confidence",
            1.0,
        )

        try:

            confidence = float(
                confidence
            )

        except (
            TypeError,
            ValueError,
        ):

            confidence = 1.0

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        selected = bool(
            assessment.get(
                "selected",
                False,
            )
        )

        if cache_key in cefr_assessment_cache:

            if selected:
                sense.cefr_level = cefr_level

            continue

        with db.no_autoflush:

            existing = db.query(
                VocabularyCEFRAssessment
            ).filter(
                VocabularyCEFRAssessment
                .vocabulary_sense_id
                == sense.id,
                VocabularyCEFRAssessment
                .cefr_level
                == cefr_level,
                VocabularyCEFRAssessment
                .source
                == source,
                VocabularyCEFRAssessment
                .source_version
                == source_version,
            ).first()

        if existing is not None:

            existing.confidence = (
                confidence
            )

        else:

            db.add(
                VocabularyCEFRAssessment(
                    vocabulary_sense_id=(
                        sense.id
                    ),
                    cefr_level=(
                        cefr_level
                    ),
                    source=source,
                    source_version=(
                        source_version
                    ),
                    confidence=(
                        confidence
                    ),
                )
            )

        cefr_assessment_cache.add(
            cache_key
        )

        created_or_updated += 1

        if selected:
            sense.cefr_level = cefr_level

    return created_or_updated


# =========================================================
# Import one record
# =========================================================

def import_record(
    row: dict[str, Any],
    db: Session,
) -> dict[str, int]:

    entry = get_or_create_entry(
        row=row,
        db=db,
    )

    sense = get_or_create_sense(
        row=row,
        entry=entry,
        db=db,
    )

    form_count = 0
    relation_count = 0

    # -----------------------------------------------------
    # Forms
    # -----------------------------------------------------

    forms = normalize_list(
        row.get("forms")
    )

    for form_data in forms:

        if add_vocabulary_form(
            entry=entry,
            form_data=form_data,
            db=db,
        ):
            form_count += 1

    # -----------------------------------------------------
    # Relations
    # -----------------------------------------------------

    relations = normalize_list(
        row.get("relations")
    )

    for relation in relations:

        if add_vocabulary_relation(
            source_entry=entry,
            relation=relation,
            db=db,
        ):
            relation_count += 1

    # -----------------------------------------------------
    # No usable sense
    # -----------------------------------------------------

    if sense is None:

        return {
            "entries": 1,
            "senses": 0,
            "localizations": 0,
            "translations": 0,
            "examples": 0,
            "example_translations": 0,
            "media": 0,
            "assessments": 0,
            "forms": form_count,
            "relations": relation_count,
        }

    localization_count = 0
    translation_count = 0
    example_count = 0
    example_translation_count = 0
    media_count = 0

    # -----------------------------------------------------
    # Localizations
    # -----------------------------------------------------

    for localization in (
        get_localization_records(row)
    ):

        if upsert_localization(
            sense=sense,
            localization=localization,
            db=db,
        ):
            localization_count += 1

    # -----------------------------------------------------
    # Translations
    # -----------------------------------------------------

    translations = normalize_list(
        row.get("translations")
    )

    for translation in translations:

        if add_translation(
            sense=sense,
            translation=translation,
            db=db,
        ):
            translation_count += 1

    # -----------------------------------------------------
    # Examples
    # -----------------------------------------------------

    examples = normalize_list(
        row.get("examples")
    )

    for example_data in examples:

        result = add_example(
            sense=sense,
            example_data=example_data,
            db=db,
        )

        if result is None:
            continue

        (
            example,
            created,
            created_translation_count,
        ) = result

        if created:
            example_count += 1

        example_translation_count += (
            created_translation_count
        )

    # -----------------------------------------------------
    # Media
    # -----------------------------------------------------

    media_items = normalize_list(
        row.get("media")
    )

    for media_data in media_items:

        if add_media(
            sense=sense,
            media_data=media_data,
            db=db,
        ):
            media_count += 1

    # -----------------------------------------------------
    # CEFR
    # -----------------------------------------------------

    assessment_count = (
        add_cefr_assessments(
            row=row,
            sense=sense,
            db=db,
        )
    )

    return {
        "entries": 1,
        "senses": 1,
        "localizations": localization_count,
        "translations": translation_count,
        "examples": example_count,
        "example_translations": (
            example_translation_count
        ),
        "media": media_count,
        "assessments": assessment_count,
        "forms": form_count,
        "relations": relation_count,
    }


# =========================================================
# Reset caches
# =========================================================

def clear_runtime_caches() -> None:

    entry_cache.clear()
    relation_target_cache.clear()
    sense_cache.clear()
    sense_candidates_cache.clear()
    sense_localization_cache.clear()
    localization_cache.clear()
    translation_cache.clear()
    example_cache.clear()
    example_translation_cache.clear()
    media_cache.clear()
    form_cache.clear()
    relation_cache.clear()
    cefr_assessment_cache.clear()


# =========================================================
# Import records
# =========================================================

def import_records(
    records: Iterator[dict[str, Any]],
    db: Session,
) -> None:

    counters = {
        "records": 0,
        "entries": 0,
        "senses": 0,
        "localizations": 0,
        "translations": 0,
        "examples": 0,
        "example_translations": 0,
        "media": 0,
        "assessments": 0,
        "forms": 0,
        "relations": 0,
        "skipped": 0,
    }

    for (
        index,
        row,
    ) in enumerate(
        records,
        start=1,
    ):

        counters["records"] += 1

        try:

            result = import_record(
                row=row,
                db=db,
            )

            for key in result:
                counters[key] += result[key]

        except Exception as exc:

            counters["skipped"] += 1

            print(
                f"Skipped record #{index}: {exc}"
            )

            db.rollback()

            # ORM objects may now be expired/invalid after
            # rollback, so caches must be cleared.
            clear_runtime_caches()

        if index % COMMIT_EVERY == 0:

            db.commit()

            print(
                f"Processed {index} converted records..."
            )

    db.commit()

    print()
    print(
        "=============================================="
    )
    print(
        "Vocabulary import completed."
    )
    print(
        "=============================================="
    )

    print(
        "Supported languages: "
        + ", ".join(
            sorted(
                SUPPORTED_LANGUAGES
            )
        )
    )

    print(
        f"Converted records: "
        f"{counters['records']}"
    )

    print(
        f"Entries: "
        f"{counters['entries']}"
    )

    print(
        f"Senses: "
        f"{counters['senses']}"
    )

    print(
        f"Localizations: "
        f"{counters['localizations']}"
    )

    print(
        f"Translations: "
        f"{counters['translations']}"
    )

    print(
        f"Examples: "
        f"{counters['examples']}"
    )

    print(
        "Example translations: "
        f"{counters['example_translations']}"
    )

    print(
        f"Media: "
        f"{counters['media']}"
    )

    print(
        f"Forms: "
        f"{counters['forms']}"
    )

    print(
        f"Relations: "
        f"{counters['relations']}"
    )

    print(
        f"CEFR assessments: "
        f"{counters['assessments']}"
    )

    print(
        f"Skipped: "
        f"{counters['skipped']}"
    )

    print()

    print(
        "Runtime cache statistics:"
    )

    print(
        f"  Entry cache hits: "
        f"{cache_stats['entry_hits']}"
    )

    print(
        f"  Entry cache misses: "
        f"{cache_stats['entry_misses']}"
    )

    print(
        f"  Relation target cache hits: "
        f"{cache_stats['relation_target_hits']}"
    )

    print(
        f"  Relation target cache misses: "
        f"{cache_stats['relation_target_misses']}"
    )

    print(
        f"  Sense cache hits: "
        f"{cache_stats['sense_hits']}"
    )

    print(
        f"  Sense cache misses: "
        f"{cache_stats['sense_misses']}"
    )

    print(
        f"  Localization cache hits: "
        f"{cache_stats['localization_hits']}"
    )

    print(
        f"  Translation cache hits: "
        f"{cache_stats['translation_hits']}"
    )

    print(
        f"  Example cache hits: "
        f"{cache_stats['example_hits']}"
    )

    print(
        f"  Media cache hits: "
        f"{cache_stats['media_hits']}"
    )

    print(
        f"  Form cache hits: "
        f"{cache_stats['form_hits']}"
    )

    print(
        f"  Relation cache hits: "
        f"{cache_stats['relation_hits']}"
    )

    print(
        "=============================================="
    )


# =========================================================
# Main
# =========================================================

def main():

    if len(sys.argv) != 2:

        print("Usage:")

        print(
            "python import_vocabulary.py "
            "path/to/file.csv"
        )

        print()

        print(
            "python import_vocabulary.py "
            "path/to/file.json"
        )

        print()

        print(
            "python import_vocabulary.py "
            "path/to/file.jsonl"
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

    print(
        "Vocabulary importer starting..."
    )

    print(
        "Supported languages: "
        + ", ".join(
            sorted(
                SUPPORTED_LANGUAGES
            )
        )
    )

    print(
        f"Commit interval: "
        f"{COMMIT_EVERY} records"
    )

    print(
        "Performance mode: "
        "runtime caches + no-autoflush lookups"
    )

    print(
        f"Input file: {file_path}"
    )

    db = SessionLocal()

    try:

        import_records(
            records=iter_records(
                file_path
            ),
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


# =========================================================
# Entry point
# =========================================================

if __name__ == "__main__":
    main()