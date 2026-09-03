import os
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv

from services.ai.client import chat_completion, stream_chat_completion


load_dotenv()


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
        model: str,
        prompt: Any,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
    ) -> Iterable[AITextResponse]:
        raise NotImplementedError


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    @staticmethod
    def _messages(
        prompt: Any,
        system_instruction: str | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction,
            })

        if isinstance(prompt, list):
            for item in prompt:
                if not isinstance(item, dict):
                    continue

                role = str(item.get("role", "user"))
                content = item.get("content")

                if content is None:
                    parts = item.get("parts")
                    if isinstance(parts, list):
                        content = "\n".join(
                            str(part.get("text", ""))
                            for part in parts
                            if isinstance(part, dict) and part.get("text")
                        )

                if content is None:
                    continue

                messages.append({
                    "role": role,
                    "content": str(content),
                })
        else:
            messages.append({
                "role": "user",
                "content": str(prompt),
            })

        return messages

    @staticmethod
    def _extract_text(message: dict[str, Any]) -> str:
        """Extract only the final answer text from OpenRouter/OpenAI content."""
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
            response_format = {"type": "json_object"}

        response = chat_completion(
            model=model,
            messages=self._messages(prompt, system_instruction),
            max_tokens=max_output_tokens,
            response_format=response_format,
        )

        choices = response.get("choices") or []
        text = ""
        finish_reason = None

        if choices:
            first_choice = choices[0] or {}
            finish_reason = first_choice.get("finish_reason")
            message = first_choice.get("message") or {}
            if isinstance(message, dict):
                text = self._extract_text(message)

        if not text:
            # Do not silently return an empty answer. This gives the caller a
            # useful failure instead of making the API look like a successful
            # translation with no content.
            raise RuntimeError(
                "OpenRouter returned no final text "
                f"(model={model!r}, finish_reason={finish_reason!r})."
            )

        usage = response.get("usage") or {}

        return AITextResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )

    def stream_text(
        self,
        *,
        model: str,
        prompt: Any,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
    ) -> Iterable[AITextResponse]:
        messages = self._messages(prompt, system_instruction)

        for chunk in stream_chat_completion(
            model=model,
            messages=messages,
            max_tokens=max_output_tokens,
        ):
            choices = chunk.get("choices") or []
            text = ""

            if choices:
                delta = choices[0].get("delta") or {}
                if isinstance(delta, dict):
                    content = delta.get("content")
                    if isinstance(content, str):
                        text = content
                    elif isinstance(content, list):
                        text = "".join(
                            str(part.get("text", ""))
                            for part in content
                            if isinstance(part, dict) and isinstance(part.get("text"), str)
                        )

            usage = chunk.get("usage") or {}

            yield AITextResponse(
                text=text,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            )


def _build_provider() -> AIProvider:
    provider_name = os.getenv("AI_PROVIDER", "openrouter").strip().lower()

    if provider_name == "openrouter":
        return OpenRouterProvider()

    raise RuntimeError(
        f"Unsupported AI_PROVIDER={provider_name!r}. "
        "The backend currently supports OpenRouter only."
    )


provider = _build_provider()
