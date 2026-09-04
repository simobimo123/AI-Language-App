import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv

from services.ai.client import chat_completion, stream_chat_completion


load_dotenv()


LESSON_PROMPT_MARKER = "You are the AI conversation partner for ONE lesson"
LESSON_MAX_OUTPUT_TOKENS = 400


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
    def _compact_lesson_instruction(system_instruction: str) -> str:
        """Keep only the lesson facts and rules the tutor needs at inference time."""
        if LESSON_PROMPT_MARKER not in system_instruction:
            return system_instruction

        def capture(pattern: str) -> str:
            match = re.search(pattern, system_instruction, flags=re.DOTALL)
            return match.group(1).strip() if match else ""

        native_language = capture(
            r"- Native language:\s*(.+?)\n- Learning language:"
        )
        learning_language = capture(
            r"- Learning language:\s*(.+?)\n- Current CEFR level:"
        )
        level = capture(r"- Current CEFR level:\s*(.+?)\n\nLESSON")
        topic = capture(r"- Topic:\s*(.*?)\n- Objective:")
        objective = capture(r"- Objective:\s*(.*?)\n\nCURRICULUM SOURCE OF TRUTH")
        targets = capture(
            r"Below are ONLY the remaining target sentences\..*?\n\n(.*?)\n\nAfter your normal learner-facing reply",
        )

        # Fail open if the expected lesson structure changes: it is safer to
        # send the original instruction than to silently remove required data.
        if not learning_language or not targets:
            return system_instruction

        return f"""You are the AI conversation partner for one language-learning lesson.

Learner native language: {native_language}
Learning language: {learning_language}
CEFR level: {level}
Topic: {topic}
Objective: {objective}

REMAINING TARGET SENTENCES
{targets}

PROGRESS TRACKING
After your learner-facing reply, append exactly one internal marker at the very end:
[[LESSON_PROGRESS:id1,id2]]
If no remaining target sentence was genuinely practiced in the learner's latest message, use:
[[LESSON_PROGRESS:]]
Only use IDs from the remaining target-sentence list.
Judge only the learner's latest message. Mark a sentence only when the learner genuinely produces its communicative meaning in the learning language. Natural wording is allowed, but merely repeating an isolated word, being shown a sentence, or hearing your correction is not enough. If you corrected the learner, wait until the learner produces the corrected meaning. Never mention the marker.

CONVERSATION RULES
- Keep the interaction natural and conversational, not a lecture or traditional lesson.
- Stay on the lesson topic and use the remaining target sentences naturally.
- Prefer learner production over tutor explanation.
- Ask one short natural question or request at a time.
- Keep replies short, normally one or two sentences.
- Correct important mistakes briefly, then ask the learner to produce the corrected sentence.
- Do not list grammar rules, vocabulary, lesson sections, or answer keys unless necessary.
- Continue naturally from the existing conversation; do not restart the lesson.
- Do not claim that a word or sentence was saved.

LANGUAGE RULES
- The conversation should normally be entirely in the learning language.
- Use the native language only for a very short clarification when the learner clearly needs help.
- Do not switch to an unrelated language or script.
- Do not automatically translate every sentence.

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
        output_limit = max_output_tokens

        if system_instruction and LESSON_PROMPT_MARKER in system_instruction:
            output_limit = min(output_limit, LESSON_MAX_OUTPUT_TOKENS)

        for chunk in stream_chat_completion(
            model=model,
            messages=messages,
            max_tokens=output_limit,
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
