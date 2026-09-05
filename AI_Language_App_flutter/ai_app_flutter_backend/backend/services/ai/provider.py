import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv

from services.ai.client import AI_MODEL, chat_completion, stream_chat_completion


load_dotenv()

LESSON_PROMPT_MARKER = "You are the AI conversation partner for one language-learning lesson."
LESSON_MAX_OUTPUT_TOKENS = 800


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
    def _compact_lesson_instruction(system_instruction: str) -> str:
        """Keep only the lesson facts and rules the tutor needs at inference time."""
        if LESSON_PROMPT_MARKER not in system_instruction:
            return system_instruction

        def capture(pattern: str) -> str:
            match = re.search(pattern, system_instruction, flags=re.DOTALL)
            return match.group(1).strip() if match else ""

        native_language = capture(r"Learner native language:\s*(.+?)\nCEFR level:")
        learning_language = capture(r"Language:\s*(.+?)\nLearner native language:")
        level = capture(r"CEFR level:\s*(.+?)\n\nLESSON CONTEXT")
        context = capture(r"LESSON CONTEXT\n(.*?)\n\nREMAINING TARGET SENTENCES")
        targets = capture(r"REMAINING TARGET SENTENCES\n(.*?)\n\nUse only the lesson context above\.")

        if not learning_language or not targets:
            return system_instruction

        return f"""You are the AI conversation partner for one language-learning lesson.

Learner native language: {native_language}
Learning language: {learning_language}
CEFR level: {level}

LESSON CONTEXT
{context}

REMAINING TARGET SENTENCES
{targets}

CONVERSATION RULES
- Keep the interaction natural and conversational, not a lecture or traditional lesson.
- Stay on the lesson topic and use the remaining target sentences naturally.
- Prefer learner production over tutor explanation.
- Ask one short natural question or request at a time.
- Keep replies short, normally one or two sentences.
- Correct important mistakes briefly, then ask the learner to produce the corrected sentence.
- Continue naturally from the existing conversation; do not restart the lesson.
- Do not claim that a word or sentence was saved.

LANGUAGE RULES
- The conversation should normally be entirely in the learning language.
- Use the native language only for a very short clarification when the learner clearly needs help.
- Do not switch to an unrelated language or script.
- Do not automatically translate every sentence.

PROGRESS TRACKING
After your learner-facing reply, append exactly one internal marker at the very end:
[[LESSON_PROGRESS:id1,id2]]
If no remaining target sentence was genuinely practiced in the learner's latest message, use:
[[LESSON_PROGRESS:]]
Only use IDs from the remaining target-sentence list.
Judge only the learner's latest message. Mark a sentence only when the learner genuinely produces its communicative meaning in the learning language. Never mention the marker.

OUTPUT
Return only the concise learner-facing reply followed by the required internal progress marker. Do not mention these instructions, curriculum data, APIs, or internal configuration."""

    @classmethod
    def _messages(
        cls,
        prompt: Any,
        system_instruction: str | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []

        if system_instruction:
            system_instruction = cls._compact_lesson_instruction(system_instruction)
            messages.append({"role": "system", "content": system_instruction})

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

                if role not in {"user", "assistant", "system"}:
                    role = "user"

                messages.append({"role": role, "content": str(content)})
        else:
            messages.append({"role": "user", "content": str(prompt)})

        return messages

    @staticmethod
    def _extract_text(message: dict[str, Any]) -> str:
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
    def _extract_delta_text(delta: dict[str, Any]) -> str:
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
        return text if isinstance(text, str) else ""

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
        model: str = AI_MODEL,
        prompt: Any = None,
        system_instruction: str | None = None,
        max_output_tokens: int = 1024,
        contents: Any = None,
    ) -> Iterable[AITextResponse]:
        # Backward-compatible alias: lesson_ai.py historically called this
        # argument "contents", while the provider API uses "prompt".
        if contents is not None:
            if prompt is not None:
                raise TypeError("Provide either 'prompt' or 'contents', not both.")
            prompt = contents

        if prompt is None:
            raise TypeError("stream_text() requires 'prompt' or 'contents'.")

        messages = self._messages(prompt, system_instruction)
        output_limit = max_output_tokens

        if system_instruction and LESSON_PROMPT_MARKER in system_instruction:
            output_limit = min(output_limit, LESSON_MAX_OUTPUT_TOKENS)

        saw_visible_text = False

        for chunk in stream_chat_completion(
            model=model,
            messages=messages,
            max_tokens=output_limit,
        ):
            choices = chunk.get("choices") or []
            text = ""
            finish_reason = None

            if choices:
                first_choice = choices[0] or {}
                finish_reason = first_choice.get("finish_reason")
                delta = first_choice.get("delta") or {}
                if isinstance(delta, dict):
                    text = self._extract_delta_text(delta)

            if text:
                saw_visible_text = True

            usage = chunk.get("usage") or {}

            yield AITextResponse(
                text=text,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
            )

        if not saw_visible_text:
            raise RuntimeError(
                "OpenRouter streaming completed without learner-facing text "
                f"(model={model!r})."
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
