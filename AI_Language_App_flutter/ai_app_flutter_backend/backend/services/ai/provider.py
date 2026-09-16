import json
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

TTS_MARKER_RE = re.compile(
    r"\[(?:NATIVE|LEARNING)\]",
    re.IGNORECASE,
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
            "Teaching AI response.\n\n"
            "**TTS SPEECH PLAN — MANDATORY INTERNAL DATA**:\n\n"
            "Add one extra JSON field named `speech_segments`. This field is internal "
            "machine-readable metadata and is never shown to the learner.\n\n"
            "`speech_segments` MUST be an array of objects in speaking order. Each object "
            "has exactly `role` and `text`. `role` MUST be either `NATIVE` or `LEARNING`.\n\n"
            "Use `NATIVE` for explanations, corrections, meanings, grammar notes, feedback, "
            "instructions, praise, and other teacher prose written in the selected explanation "
            "language. Use `LEARNING` for target words, target sentences, examples, model "
            "answers, answer patterns, and learner-production content written in the language "
            "being learned.\n\n"
            "The concatenated speech segment texts, in order, MUST reproduce the visible `reply` "
            "content exactly apart from insignificant whitespace differences. Do not omit any "
            "spoken words from `reply`. Do not add words that are absent from `reply`.\n\n"
            "Keep segments reasonably large; do not create one segment per word. Split only when "
            "the spoken language actually changes. The `reply` field itself MUST NOT contain "
            "`[NATIVE]` or `[LEARNING]` markers.\n\n"
            "Example: if the visible reply is `هذا يعني أن اسمك يأتي بعد ich heiße. مثال: Ich heiße Anna.` "
            "then the speech plan should use one NATIVE segment for the Arabic explanation and one "
            "LEARNING segment for the German example. The learner must never see the speech metadata.\n\n"
            "Return valid JSON that contains the normal lesson fields plus `speech_segments`."
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

                cleaned_content = TTS_MARKER_RE.sub(
                    "",
                    str(content),
                )

                messages.append(
                    {
                        "role": role,
                        "content": cleaned_content,
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

        return visible.strip()

    @classmethod
    def _normalize_teaching_tts_response(
        cls,
        text: str,
        system_instruction: str | None,
    ) -> str:
        """Validate the teaching TTS plan and encode it into private markers."""
        if not system_instruction or "You are the **TEACHING AI**" not in system_instruction:
            return text

        try:
            payload = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return text

        if not isinstance(payload, dict):
            return text

        reply = str(payload.get("reply") or "").strip()
        if not reply:
            return text

        raw_segments = payload.get("speech_segments")
        valid_segments: list[tuple[str, str]] = []

        if isinstance(raw_segments, list):
            for item in raw_segments:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "").strip().upper()
                segment_text = str(item.get("text") or "").strip()
                if role not in {"NATIVE", "LEARNING"} or not segment_text:
                    continue
                valid_segments.append((role, segment_text))

        if not valid_segments:
            return text

        reconstructed = "".join(segment_text for _, segment_text in valid_segments).strip()
        normalized_reply = re.sub(r"\s+", " ", reply).strip()
        normalized_reconstructed = re.sub(r"\s+", " ", reconstructed).strip()

        if normalized_reply != normalized_reconstructed:
            return text

        private_reply_parts: list[str] = []
        for role, segment_text in valid_segments:
            private_reply_parts.append(f"[{role}] {segment_text}")

        payload["reply"] = " ".join(private_reply_parts)
        payload.pop("speech_segments", None)

        return json.dumps(payload, ensure_ascii=False)

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

        text = self._normalize_teaching_tts_response(
            text,
            system_instruction,
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
            # Do NOT add a lesson progress marker here.
            # The real marker generated by the model remains inside
            # buffered_lesson_text and is passed to lesson_ai.py.

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
