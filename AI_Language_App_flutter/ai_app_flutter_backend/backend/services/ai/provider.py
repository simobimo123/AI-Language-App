import os
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


@dataclass(frozen=True)
class AITextResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AIProvider:
    """Small provider interface used by application-level AI services.

    The rest of the application should depend on these methods rather than
    importing a provider SDK directly. This makes the provider replaceable.
    """

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


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str) -> None:
        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _usage(response: Any) -> tuple[int, int, int]:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return 0, 0, 0

        prompt_tokens = int(
            getattr(usage, "prompt_token_count", 0) or 0
        )
        completion_tokens = int(
            getattr(usage, "candidates_token_count", 0) or 0
        )
        total_tokens = int(
            getattr(usage, "total_token_count", 0) or 0
        )
        return prompt_tokens, completion_tokens, total_tokens

    def generate_text(
        self,
        *,
        model: str,
        prompt: str,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        response_mime_type: str | None = None,
    ) -> AITextResponse:
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_output_tokens,
        }

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        if response_mime_type:
            config_kwargs["response_mime_type"] = response_mime_type

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        prompt_tokens, completion_tokens, total_tokens = self._usage(response)
        return AITextResponse(
            text=getattr(response, "text", "") or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def stream_text(
        self,
        *,
        model: str,
        prompt: Any,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
    ) -> Iterable[AITextResponse]:
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": max_output_tokens,
        }

        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        response_stream = self.client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        for chunk in response_stream:
            prompt_tokens, completion_tokens, total_tokens = self._usage(chunk)
            yield AITextResponse(
                text=getattr(chunk, "text", "") or "",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )


def _build_provider() -> AIProvider:
    provider_name = os.getenv("AI_PROVIDER", "gemini").strip().lower()

    if provider_name == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in the .env file"
            )
        return GeminiProvider(api_key)

    raise RuntimeError(
        f"Unsupported AI_PROVIDER={provider_name!r}. "
        "Add a provider implementation before selecting it."
    )


provider = _build_provider()
