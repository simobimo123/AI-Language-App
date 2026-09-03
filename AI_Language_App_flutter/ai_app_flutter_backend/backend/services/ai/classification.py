import json
import logging

from models import User
from services.ai.client import AI_CLASSIFIER_MODEL, chat_completion
from services.ai.usage import extract_token_usage
from services.ai.schemas import AIRequestClassification


logger = logging.getLogger(__name__)


NORMAL_MAX_OUTPUT_TOKENS = 1200
MEDIUM_MAX_OUTPUT_TOKENS = 3000
LONG_MAX_OUTPUT_TOKENS = 4096


CLASSIFIER_SYSTEM_INSTRUCTION = """
You are a request classifier for a multilingual
language-learning application.

Your ONLY job is to classify the user's request.

Return structured JSON.

decision:
ALLOW
LIMIT
BLOCK

reason:
A short explanation.

needs_vocabulary_enrichment:
true or false

vocabulary_word:
The specific vocabulary item the user is asking about,
or null.

vocabulary_request_type:
meaning
translation
definition
example
pronunciation
general
none

==================================================
APPLICATION PURPOSE
==================================================

The application is for:

- learning languages
- vocabulary
- grammar
- pronunciation
- reading
- writing
- translation for language learning
- conversation practice
- error correction
- exercises
- explanations
- useful discussion as language practice

==================================================
CLASSIFICATION
==================================================

ALLOW:
Reasonably related to language learning or conversation practice.

LIMIT:
Useful but unusually large.

Examples:
"Give me 1000 vocabulary words."
"Give me 5000 example sentences."

BLOCK:
Clearly unrelated to language learning.

When ambiguity exists, prefer ALLOW.

==================================================
VOCABULARY
==================================================

Set needs_vocabulary_enrichment=true ONLY when the user is
asking about a specific word.

"What does environment mean?"
→ true

"Translate environment."
→ true

"Give me an example with environment."
→ true

"How do I pronounce environment?"
→ true

"Let's talk about the environment."
→ false

Do not invent a vocabulary word.

The user's native and learning languages are supplied in context.

==================================================
FINAL RULE
==================================================

Understand the user's intent and return only structured JSON.
"""


def classify_ai_request(
    message: str,
    current_user: User,
) -> tuple[
    AIRequestClassification,
    int,
    int,
    int,
]:
    classifier_context = f"""
USER PROFILE

Native language:
{current_user.native_language}

Learning language:
{current_user.learning_language}

USER REQUEST:
{message}
"""

    try:
        response = chat_completion(
            model=AI_CLASSIFIER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": CLASSIFIER_SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": classifier_context,
                },
            ],
            max_tokens=180,
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
                "OpenRouter classifier returned an empty response."
            )

        usage = response.get("usage") or {}
        prompt_tokens, completion_tokens, total_tokens = extract_token_usage(
            usage
        )

        result = AIRequestClassification.model_validate(
            json.loads(content)
        )

        logger.info(
            "AI classifier user_id=%s decision=%s vocabulary=%s word=%s type=%s",
            current_user.id,
            result.decision,
            result.needs_vocabulary_enrichment,
            result.vocabulary_word,
            result.vocabulary_request_type,
        )

        return (
            result,
            prompt_tokens,
            completion_tokens,
            total_tokens,
        )

    except Exception as exc:
        logger.exception(
            "AI classifier failed user_id=%s: %s",
            current_user.id,
            exc,
        )

        return (
            AIRequestClassification(
                decision="ALLOW",
                reason="Classifier unavailable; allowing request.",
                needs_vocabulary_enrichment=False,
                vocabulary_word=None,
                vocabulary_request_type="none",
            ),
            0,
            0,
            0,
        )


def get_max_output_tokens(
    classification: AIRequestClassification,
) -> int:
    if classification.decision == "LIMIT":
        return MEDIUM_MAX_OUTPUT_TOKENS

    return NORMAL_MAX_OUTPUT_TOKENS
