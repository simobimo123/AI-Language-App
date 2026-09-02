import json
import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from models import CourseLesson
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider


logger = logging.getLogger(__name__)


class LessonVocabularyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    word: str = Field(min_length=1)
    translation: str = Field(min_length=1)
    part_of_speech: str | None = None
    pronunciation: str | None = None


class LessonExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_text: str = Field(min_length=1)
    translation: str = Field(min_length=1)


class LessonExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    answer: str = Field(min_length=1)
    explanation: str | None = None


class GeneratedLessonContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    introduction: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    vocabulary: list[LessonVocabularyItem] = Field(min_length=1, max_length=15)
    examples: list[LessonExample] = Field(min_length=1, max_length=10)
    dialogue: list[LessonExample] = Field(default_factory=list, max_length=10)
    exercises: list[LessonExercise] = Field(min_length=5, max_length=15)


LESSON_GENERATION_INSTRUCTION = """
You are the curriculum content generator for a multilingual language-learning app.

Generate ONE complete lesson from the supplied curriculum metadata.
The curriculum order and topic are controlled by the application. Do not change
or invent the lesson level or topic.

The lesson must be pedagogically appropriate for the CEFR level.
Use natural, correct language for the target language.
Avoid advanced grammar and vocabulary when the level is beginner.
Do not mention that AI generated the lesson.

Return ONLY valid JSON. Do not use Markdown fences.

JSON fields:
- title
- objective
- introduction
- explanation
- vocabulary
- examples
- dialogue
- exercises

Vocabulary items must contain: word, translation, part_of_speech, pronunciation.
Examples and dialogue items must contain: target_text, translation.
Exercises must contain: type, question, options, answer, explanation.

Exercise types should be selected from useful formats such as:
- multiple_choice
- fill_blank
- translation
- word_order

For multiple_choice, provide 3 or 4 options and make answer exactly one option.
For fill_blank, answer must be the missing target-language text.
For word_order, options should be the shuffled words and answer should be the
correct ordered sentence.

The translation/explanation language is supplied separately.
Never use English as a fallback when another instruction language is requested.
"""


def _clean_json_response(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def _validate_exercises(content: GeneratedLessonContent) -> None:
    for exercise in content.exercises:
        if exercise.type == "multiple_choice":
            if len(exercise.options) < 3:
                raise ValueError("Multiple-choice exercise needs at least 3 options.")
            if exercise.answer not in exercise.options:
                raise ValueError("Multiple-choice answer must be one of the options.")

        if exercise.type == "word_order":
            if len(exercise.options) < 2:
                raise ValueError("Word-order exercise needs at least 2 word options.")


def generate_lesson_content(
    lesson: CourseLesson,
    instruction_language: str = "ar",
) -> tuple[GeneratedLessonContent, int, int, int]:
    target_language = normalize_language(lesson.language)
    level = normalize_level(lesson.level)
    instruction_language = normalize_language(instruction_language)

    prompt = f"""
TARGET LANGUAGE:
{target_language}

CEFR LEVEL:
{level}

LESSON ORDER:
{lesson.lesson_order}

UNIT:
{lesson.unit_number}

TOPIC KEY:
{lesson.topic_key}

INSTRUCTION / TRANSLATION LANGUAGE:
{instruction_language}

Generate a self-contained lesson for a language-learning application.

Requirements:
- 8 to 12 vocabulary items.
- 3 to 6 examples.
- A short practical dialogue when appropriate.
- 8 to 12 exercises.
- Keep the lesson focused on the supplied topic.
- Vocabulary and target sentences must be in {target_language}.
- Translations, explanations, and objectives must be in {instruction_language}.
- Exercises must test the lesson content, not unrelated material.
- Do not introduce vocabulary that is unnecessarily difficult for {level}.
- Keep content concise enough for a mobile app.

Return JSON only.
"""

    response = provider.generate_text(
        model="lesson-generation",
        prompt=prompt,
        system_instruction=LESSON_GENERATION_INSTRUCTION,
        max_output_tokens=4000,
        response_mime_type="application/json",
    )

    if not response.text:
        raise RuntimeError(
            f"{provider.name} returned an empty lesson response."
        )

    cleaned = _clean_json_response(response.text)

    try:
        raw_data = json.loads(cleaned)
        content = GeneratedLessonContent.model_validate(raw_data)
        _validate_exercises(content)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.error(
            "Invalid generated lesson JSON lesson_id=%s: %s response=%s",
            lesson.id,
            exc,
            cleaned[:5000],
        )
        raise RuntimeError(
            f"{provider.name} returned invalid lesson content JSON."
        ) from exc

    return (
        content,
        response.prompt_tokens,
        response.completion_tokens,
        response.total_tokens,
    )
