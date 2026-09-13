import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv

from services.ai.client import (
    AI_MODEL,
    chat_completion,
    stream_chat_completion,
)
from services.ai.explanation_language_context import (
    get_explanation_language_context,
)

load_dotenv()


LESSON_PROMPT_MARKER = (
    "You are an AI tutor conducting a guided natural conversation practice."
)

LESSON_MAX_OUTPUT_TOKENS = 2048

LESSON_PROGRESS_RE = re.compile(
    r"\[\[LESSON_PROGRESS:([^\]\r\n]*)\]\]"
)


@dataclass(frozen=True)
class AITextResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIProvider:
    """Provider interface used by application-level AI services."""

    name: str

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        response_mime_type: str | None = None,
    ) -> AITextResponse:
        raise NotImplementedError

    def stream_text(
        self,
        *,
        model: str = AI_MODEL,
        prompt: Any = None,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        contents: Any = None,
    ) -> Iterable[AITextResponse]:
        raise NotImplementedError


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    @staticmethod
    def _language_name(code: str) -> str:
        names = {
            "ar": "Arabic",
            "de": "German",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "id": "Indonesian",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "nl": "Dutch",
            "pl": "Polish",
            "pt": "Portuguese",
            "ru": "Russian",
            "th": "Thai",
            "tr": "Turkish",
            "uk": "Ukrainian",
            "vi": "Vietnamese",
            "zh": "Chinese",
        }
        normalized = code.strip().lower()
        return names.get(normalized, normalized)

    @classmethod
    def _apply_teaching_explanation_language(
        cls,
        system_instruction: str | None,
    ) -> str | None:
        if not system_instruction:
            return system_instruction

        if "You are the **TEACHING AI**" not in system_instruction:
            return system_instruction

        context = get_explanation_language_context()

        if context is None:
            return system_instruction

        mode, native_language, learning_language = context

        explanation_language_code = (
            native_language
            if mode == "native"
            else learning_language
        )
        explanation_language = cls._language_name(
            explanation_language_code
        )

        learning_language_name = cls._language_name(
            learning_language
        )

        language_source = (
            "the learner's native language"
            if mode == "native"
            else "the learner's language of study"
        )

        return (
            f"{system_instruction}\n\n"
            "**LANGUAGE ROLES — MANDATORY**:\n\n"
            f"The learner is learning **{learning_language_name}** "
            f"(language code: **{learning_language}**). "
            f"Your explanation language is **{explanation_language}** "
            f"(language code: **{explanation_language_code}**).\n\n"
            f"The learner's goal is to learn **{learning_language_name}**. "
            f"You MUST use **{explanation_language}** for all explanations, "
            "corrections, grammar notes, word meanings, error explanations, "
            "instructions, and teacher feedback. The selected explanation "
            f"language comes from {language_source}.\n\n"
            f"Use **{learning_language_name}** for target sentences, example "
            "sentences, model answers, and language the learner is expected "
            "to produce or practice. These are learning-language content, "
            "not explanations.\n\n"
            f"When correcting an answer, explain the correction in "
            f"**{explanation_language}**, while keeping the corrected/model "
            f"sentence itself in **{learning_language_name}**.\n\n"
            f"The learner is allowed to communicate with you in **{explanation_language}**, "
            f"in **{learning_language_name}**, or in both. You MUST understand the learner's "
            "message regardless of which of these languages they use. Never claim that you "
            f"do not understand simply because the learner used **{explanation_language}**. "
            "Do not force the learner to use the learning language for communication with "
            "the teacher; require the learning language only when the CURRENT TARGET requires "
            "the learner to produce it.\n\n"
            f"Do NOT use **{learning_language_name}** for teacher prose just "
            "because it is the language being learned. **In the reply field, every "
            "ordinary teacher word MUST use the selected explanation language.** "
            f"Do NOT write praise, transitions, corrections, instructions, or feedback "
            f"in **{learning_language_name}** unless it is also the selected explanation "
            "language. The learning language is allowed in the reply only for target "
            "sentences, examples, model answers, or learner practice content. "
            "Do NOT silently switch the explanation language to English or the learning "
            "language. The selected explanation language remains fixed for the entire "
            "Teaching AI response."
        )

    @classmethod
    def _messages(
        cls,
        prompt: Any,
        system_instruction: str | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_instruction:
            messages.append(
                {
                    "role": "system",
                    "content": cls._apply_teaching_explanation_language(
                        system_instruction
                    ) or system_instruction,
                }
            )

        if isinstance(prompt, list):
            for item in prompt:
                if not isinstance(item, dict):
                    continue

                role = str(
                    item.get(
                        "role",
                        "user",
                    )
                )

                content = item.get("content")

                if content is None:
                    parts = item.get("parts")

                    if isinstance(parts, list):
                        content = "\n".join(
                            str(
                                part.get(
                                    "text",
                                    "",
                                )
                            )
                            for part in parts
                            if (
                                isinstance(part, dict)
                                and part.get("text")
                            )
                        )

                if content is None:
                    continue

                if role not in {
                    "user",
                    "assistant",
                    "system",
                }:
                    role = "user"

                messages.append(
                    {
                        "role": role,
                        "content": str(content),
                    }
                )

        else:
            messages.append(
                {
                    "role": "user",
                    "content": str(prompt),
                }
            )

        return messages

    @staticmethod
    def _extract_text(
        message: dict[str, Any],
    ) -> str:
        """Extract final learner-facing text without exposing reasoning."""

        content = message.get("content")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts: list[str] = []

            for part in content:
                if isinstance(part, str):
                    parts.append(part)

                elif isinstance(part, dict):
                    text = part.get("text")

                    if isinstance(text, str):
                        parts.append(text)

            return "".join(parts).strip()

        return ""

    @staticmethod
    def _extract_delta_text(
        delta: dict[str, Any],
    ) -> str:
        """Extract streamed visible text from OpenRouter/OpenAI delta shapes."""

        content = delta.get("content")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: list[str] = []

            for part in content:
                if isinstance(part, str):
                    parts.append(part)

                elif isinstance(part, dict):
                    text = part.get("text")

                    if isinstance(text, str):
                        parts.append(text)

            return "".join(parts)

        text = delta.get("text")

        return (
            text
            if isinstance(text, str)
            else ""
        )

    @staticmethod
    def _remove_exact_duplicate_response(
        text: str,
    ) -> str:
        """
        Collapse a response that consists of the same complete reply twice.
        """

        cleaned = re.sub(
            r"[\u200b\u200c\u200d\ufeff]",
            "",
            text,
        ).strip()

        if not cleaned:
            return cleaned

        match = re.fullmatch(
            r"(.+?)\s+\1",
            cleaned,
            flags=re.DOTALL,
        )

        if match:
            return match.group(1).strip()

        normalized = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip()

        if normalized != cleaned:
            match = re.fullmatch(
                r"(.+?)\s+\1",
                normalized,
                flags=re.DOTALL,
            )

            if match:
                return match.group(1).strip()

        return cleaned

    @classmethod
    def _clean_lesson_response(
        cls,
        text: str,
    ) -> str:
        """
        Remove accidental duplicate text while preserving the real
        lesson progress marker generated by the model.

        IMPORTANT:
        This method never creates a progress marker.
        """

        visible = LESSON_PROGRESS_RE.sub(
            "",
            text,
        )

        visible = cls._remove_exact_duplicate_response(
            visible
        )

        # The provider must NOT re-attach the marker.
        #
        # lesson_ai.py receives the original stream separately and
        # extracts the marker there.
        return visible.strip()

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        response_mime_type: str | None = None,
    ) -> AITextResponse:
        response_format = None

        if response_mime_type == "application/json":
            response_format = {
                "type": "json_object"
            }

        response = chat_completion(
            model=model,
            messages=self._messages(
                prompt,
                system_instruction,
            ),
            max_tokens=max_output_tokens,
            response_format=response_format,
        )

        choices = response.get(
            "choices"
        ) or []

        text = ""
        finish_reason = None

        if choices:
            first_choice = choices[0] or {}

            finish_reason = first_choice.get(
                "finish_reason"
            )

            message = first_choice.get(
                "message"
            ) or {}

            if isinstance(
                message,
                dict,
            ):
                text = self._extract_text(
                    message
                )

        if not text:
            raise RuntimeError(
                "OpenRouter returned no final text "
                f"(model={model!r}, "
                f"finish_reason={finish_reason!r})."
            )

        usage = response.get(
            "usage"
        ) or {}

        return AITextResponse(
            text=text,
            prompt_tokens=int(
                usage.get(
                    "prompt_tokens",
                    0,
                )
                or 0
            ),
            completion_tokens=int(
                usage.get(
                    "completion_tokens",
                    0,
                )
                or 0
            ),
            total_tokens=int(
                usage.get(
                    "total_tokens",
                    0,
                )
                or 0
            ),
        )

    def stream_text(
        self,
        *,
        model: str = AI_MODEL,
        prompt: Any = None,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        contents: Any = None,
    ) -> Iterable[AITextResponse]:
        if contents is not None:
            if prompt is not None:
                raise TypeError(
                    "Provide either 'prompt' or 'contents', not both."
                )

            prompt = contents

        if prompt is None:
            raise TypeError(
                "stream_text() requires 'prompt' or 'contents'."
            )

        messages = self._messages(
            prompt,
            system_instruction,
        )

        output_limit = max_output_tokens

        is_lesson = bool(
            system_instruction
            and LESSON_PROMPT_MARKER
            in system_instruction
        )

        if is_lesson:
            output_limit = min(
                output_limit,
                LESSON_MAX_OUTPUT_TOKENS,
            )

        saw_visible_text = False

        buffered_lesson_text = ""

        buffered_prompt_tokens = 0
        buffered_completion_tokens = 0
        buffered_total_tokens = 0

        for chunk in stream_chat_completion(
            model=model,
            messages=messages,
            max_tokens=output_limit,
        ):
            choices = chunk.get(
                "choices"
            ) or []

            text = ""

            if choices:
                first_choice = choices[0] or {}

                delta = first_choice.get(
                    "delta"
                ) or {}

                if isinstance(
                    delta,
                    dict,
                ):
                    text = self._extract_delta_text(
                        delta
                    )

            usage = chunk.get(
                "usage"
            ) or {}

            prompt_tokens = int(
                usage.get(
                    "prompt_tokens",
                    0,
                )
                or 0
            )

            completion_tokens = int(
                usage.get(
                    "completion_tokens",
                    0,
                )
                or 0
            )

            total_tokens = int(
                usage.get(
                    "total_tokens",
                    0,
                )
                or 0
            )

            if is_lesson:
                if text:
                    saw_visible_text = True
                    buffered_lesson_text += text

                if prompt_tokens:
                    buffered_prompt_tokens = (
                        prompt_tokens
                    )

                if completion_tokens:
                    buffered_completion_tokens = (
                        completion_tokens
                    )

                if total_tokens:
                    buffered_total_tokens = (
                        total_tokens
                    )

                # Lesson responses are intentionally buffered.
                #
                # This allows lesson_ai.py to see the complete internal
                # progress marker before sending learner-facing text.
                continue

            if text:
                saw_visible_text = True

            yield AITextResponse(
                text=text,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

        if not saw_visible_text:
            raise RuntimeError(
                "OpenRouter streaming completed without "
                "learner-facing text "
                f"(model={model!r})."
            )

        if is_lesson:
            cleaned = self._clean_lesson_response(
                buffered_lesson_text
            )

            if not cleaned:
                raise RuntimeError(
                    "OpenRouter lesson response became empty "
                    "after cleanup "
                    f"(model={model!r})."
                )

            # IMPORTANT:
            #
            # Do NOT add:
            #
            # [[LESSON_PROGRESS:]]
            #
            # here.
            #
            # The real marker generated by MiniMax remains inside
            # buffered_lesson_text and is passed to lesson_ai.py.
            #
            # lesson_ai.py extracts it before exposing text to Flutter.

            yield AITextResponse(
                text=buffered_lesson_text,
                prompt_tokens=buffered_prompt_tokens,
                completion_tokens=buffered_completion_tokens,
                total_tokens=buffered_total_tokens,
            )


def _build_provider() -> AIProvider:
    provider_name = os.getenv(
        "AI_PROVIDER",
        "openrouter",
    ).strip().lower()

    if provider_name == "openrouter":
        return OpenRouterProvider()

    raise RuntimeError(
        f"Unsupported AI_PROVIDER={provider_name!r}. "
        "The backend currently supports OpenRouter only."
    )


provider = _build_provider()
