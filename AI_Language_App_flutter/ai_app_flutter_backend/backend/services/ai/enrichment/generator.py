import json
import logging

from models import User
from services.ai.client import AI_MODEL, chat_completion
from services.ai.normalization import (
    normalize_confidence,
    normalize_language,
    normalize_text,
)
from services.ai.schemas import AIVocabularyEnrichment
from services.ai.usage import extract_token_usage


logger = logging.getLogger(__name__)


VOCABULARY_ENRICHMENT_INSTRUCTION = """
You are the vocabulary knowledge-enrichment engine of a
multilingual language-learning application.

The database is the source of truth.

Your job is to fill missing information for ONE lexical item.

Do not replace correct existing information.

Do not invent application-specific facts.

==================================================
LANGUAGE ASSIGNMENT - VERY IMPORTANT
==================================================

There are TWO languages in this request.

1. LEARNING LANGUAGE
2. NATIVE LANGUAGE

You MUST keep every generated field in its correct language.

LEARNING LANGUAGE:
__LEARNING_LANGUAGE__

NATIVE LANGUAGE:
__NATIVE_LANGUAGE__

==================================================
FIELD LANGUAGE RULES
==================================================

The following fields MUST be written in the
LEARNING LANGUAGE:

- meaning
- definition
- example_sentence
- forms
- relation target words such as synonym and antonym

The following fields MUST be written in the
NATIVE LANGUAGE:

- native_translation
- native_definition
- example_translations.translation

The field "language" MUST equal the LEARNING LANGUAGE.

==================================================
CRITICAL RULE
==================================================

NEVER use English as a fallback language.

For example, if:

Learning language = de
Native language = ar

Then this is WRONG:

meaning:
"fast, quick, rapid"

because that is English.

Instead, the meaning MUST be German.

For example:

meaning:
"schnell, mit hoher Geschwindigkeit"

definition:
"Mit hoher Geschwindigkeit oder in kurzer Zeit."

Likewise:

native_translation:
"سريع"

native_definition:
"يتحرك أو يحدث بسرعة عالية."

The language of each field must match its assigned language,
even if the AI model internally reasons in English.

==================================================
RELATIONS
==================================================

All relation words MUST be in the LEARNING LANGUAGE.

Examples:

{
  "word": "langsam",
  "relation_type": "antonym"
}

{
  "word": "rasch",
  "relation_type": "synonym"
}

Do not return English synonyms for a German word.

Do not translate relation words into the native language.

==================================================
EXAMPLE
==================================================

example_sentence MUST be in the LEARNING LANGUAGE.

example_translations MUST be in the NATIVE LANGUAGE.

Example:

Learning language = de
Native language = ar

example_sentence:
"Er läuft sehr schnell."

example_translations:
[
  {
    "language": "ar",
    "translation": "هو يركض بسرعة كبيرة."
  }
]

==================================================
OUTPUT
==================================================

Return ONLY valid JSON.

The JSON object must contain:

word
language
part_of_speech
pronunciation
cefr_level
cefr_confidence
meaning
definition
native_translation
native_definition
forms
relations
example_sentence
example_translations

If a value is unavailable, use null.

Lists with no useful items must be [].

==================================================
CEFR
==================================================

Use only:

PRE_A1
A1
A2
B1
B2
C1
C2

cefr_confidence must be a number from 0.0 to 1.0.

==================================================
FORMS
==================================================

Forms must be in the LEARNING LANGUAGE.

Each form must use:

{
  "form": "...",
  "form_type": "...",
  "is_lemma": true
}

Never use "value" instead of "form".

==================================================
IMPORTANT FINAL CHECK
==================================================

Before returning the JSON, verify:

- meaning = LEARNING LANGUAGE
- definition = LEARNING LANGUAGE
- forms = LEARNING LANGUAGE
- relation words = LEARNING LANGUAGE
- example_sentence = LEARNING LANGUAGE
- native_translation = NATIVE LANGUAGE
- native_definition = NATIVE LANGUAGE
- example translations = NATIVE LANGUAGE
- language = LEARNING LANGUAGE

If any field is in the wrong language, correct it before returning JSON.

Return valid JSON only.
"""


def clean_json_response(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def generate_vocabulary_enrichment(
    word: str,
    current_user: User,
    existing_context: str,
) -> tuple[
    AIVocabularyEnrichment,
    int,
    int,
    int,
]:
    learning_language = normalize_language(
        current_user.learning_language
    )

    native_language = normalize_language(
        current_user.native_language
    )

    instruction = (
        VOCABULARY_ENRICHMENT_INSTRUCTION
        .replace("__LEARNING_LANGUAGE__", learning_language)
        .replace("__NATIVE_LANGUAGE__", native_language)
    )

    prompt = f"""
TARGET WORD:
{word}

==================================================
USER LANGUAGE PROFILE
==================================================

LEARNING LANGUAGE:
{learning_language}

NATIVE LANGUAGE:
{native_language}

==================================================
STRICT LANGUAGE REQUIREMENTS
==================================================

meaning:
MUST be written in {learning_language}

definition:
MUST be written in {learning_language}

forms:
MUST be written in {learning_language}

relations.word:
MUST be written in {learning_language}

example_sentence:
MUST be written in {learning_language}

native_translation:
MUST be written in {native_language}

native_definition:
MUST be written in {native_language}

example_translations[].translation:
MUST be written in {native_language}

language:
MUST be "{learning_language}"

DO NOT use English as a fallback language.

==================================================
EXISTING DATABASE CONTEXT
==================================================

{existing_context}

==================================================
TASK
==================================================

Fill the missing vocabulary information.

Important:

- Preserve correct existing information.
- Generate information primarily for missing fields.
- The response will be saved in the application database.
- Return ONLY valid JSON.
- Do not use Markdown fences.
- Every relation must use "word", never "target_word".
- Every relation word must be in the learning language.
- Every form must use "form", never "value".
- Every form must be in the learning language.
- Every example translation must be an object with
  "language" and "translation".
- Every example translation must be in the native language.
- cefr_confidence must be a number between 0 and 1.
- Do not use English for meaning or definition when the
  learning language is not English.
"""

    response = chat_completion(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": instruction,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        max_tokens=1800,
        response_format={
            "type": "json_object",
        },
    )

    content = (
        response.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not content:
        raise RuntimeError(
            "OpenRouter vocabulary enrichment returned an empty response."
        )

    usage = response.get("usage") or {}
    prompt_tokens, completion_tokens, total_tokens = extract_token_usage(
        usage
    )

    cleaned_json = clean_json_response(content)

    try:
        raw_data = json.loads(cleaned_json)

        if not isinstance(raw_data, dict):
            raise ValueError(
                "OpenRouter vocabulary response must be a JSON object."
            )

        if not raw_data.get("word"):
            raw_data["word"] = word

        raw_data["language"] = learning_language

        raw_data["cefr_confidence"] = normalize_confidence(
            raw_data.get("cefr_confidence")
        )

        normalized_forms = []

        for form_data in raw_data.get("forms", []) or []:
            if isinstance(form_data, str):
                form_value = form_data.strip()
                if form_value:
                    normalized_forms.append(
                        {
                            "form": form_value,
                            "form_type": None,
                            "is_lemma": normalize_text(form_value)
                            == normalize_text(word),
                            "grammatical_features": None,
                        }
                    )
                continue

            if not isinstance(form_data, dict):
                continue

            form_value = (
                form_data.get("form")
                or form_data.get("value")
                or form_data.get("word")
            )

            if not form_value:
                continue

            normalized_forms.append(
                {
                    "form": str(form_value).strip(),
                    "form_type": (
                        str(form_data.get("form_type")).strip()
                        if form_data.get("form_type")
                        else None
                    ),
                    "is_lemma": bool(form_data.get("is_lemma", False)),
                    "grammatical_features": (
                        form_data.get("grammatical_features")
                        if isinstance(form_data.get("grammatical_features"), dict)
                        else None
                    ),
                }
            )

        raw_data["forms"] = normalized_forms

        requested_normalized = normalize_text(word)
        normalized_form_values = {
            normalize_text(item["form"])
            for item in normalized_forms
            if item.get("form")
        }

        if requested_normalized not in normalized_form_values:
            raw_data["forms"].insert(
                0,
                {
                    "form": word,
                    "form_type": "lemma",
                    "is_lemma": True,
                    "grammatical_features": None,
                },
            )

        normalized_relations = []
        allowed_relation_types = {
            "synonym",
            "antonym",
            "related",
            "derived",
            "hypernym",
            "hyponym",
            "holonym",
            "meronym",
            "coordinate_term",
            "see_also",
        }

        for relation_data in raw_data.get("relations", []) or []:
            if not isinstance(relation_data, dict):
                continue

            target_word = (
                relation_data.get("word")
                or relation_data.get("target_word")
            )
            relation_type = relation_data.get("relation_type")

            if not target_word or not relation_type:
                continue

            relation_type = str(relation_type).strip().lower()
            if relation_type not in allowed_relation_types:
                continue

            normalized_relations.append(
                {
                    "word": str(target_word).strip(),
                    "relation_type": relation_type,
                    "part_of_speech": relation_data.get("part_of_speech"),
                }
            )

        raw_data["relations"] = normalized_relations

        normalized_translations = []

        for translation_data in raw_data.get("example_translations", []) or []:
            if isinstance(translation_data, str):
                translation_text = translation_data.strip()
                if translation_text:
                    normalized_translations.append(
                        {
                            "language": native_language,
                            "translation": translation_text,
                        }
                    )
                continue

            if not isinstance(translation_data, dict):
                continue

            translation_text = (
                translation_data.get("translation")
                or translation_data.get("text")
                or translation_data.get("value")
            )

            if not translation_text:
                continue

            normalized_translations.append(
                {
                    "language": native_language,
                    "translation": str(translation_text).strip(),
                }
            )

        raw_data["example_translations"] = normalized_translations

        if raw_data.get("cefr_level"):
            raw_data["cefr_level"] = str(
                raw_data["cefr_level"]
            ).strip().upper()

        result = AIVocabularyEnrichment.model_validate(raw_data)

    except Exception as exc:
        logger.error(
            "Invalid vocabulary enrichment JSON for word=%s: %s response=%s",
            word,
            exc,
            cleaned_json[:5000],
        )
        raise RuntimeError(
            "OpenRouter returned invalid vocabulary JSON."
        ) from exc

    return (
        result,
        prompt_tokens,
        completion_tokens,
        total_tokens,
    )
