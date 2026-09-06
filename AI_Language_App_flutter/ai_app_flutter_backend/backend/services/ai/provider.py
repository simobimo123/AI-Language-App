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
                    "content": system_instruction,
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