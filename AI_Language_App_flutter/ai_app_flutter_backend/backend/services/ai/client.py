import os
from pathlib import Path

from dotenv import load_dotenv


_BASE_DIR = Path(__file__).resolve().parents[3]
_ENV_PATH = _BASE_DIR / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)
load_dotenv(override=False)

OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured in the backend .env file"
    )

OPENROUTER_BASE_URL = (
    os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    .strip()
    .rstrip("/")
)

AI_MODEL = os.getenv(
    "OPENROUTER_MAIN_MODEL",
    "minimax/minimax-m2.7:free",
).strip()

AI_CLASSIFIER_MODEL = os.getenv(
    "OPENROUTER_CLASSIFIER_MODEL",
    AI_MODEL,
).strip()

if not AI_MODEL:
    raise RuntimeError("OPENROUTER_MAIN_MODEL is empty in the .env file")

if not AI_CLASSIFIER_MODEL:
    raise RuntimeError("OPENROUTER_CLASSIFIER_MODEL is empty in the .env file")


# Lesson AI already computes the complete pedagogical state on the backend.
# The model therefore only needs a very small recent conversational window.
# This keeps the full lesson memory in the database without repeatedly sending
# the entire conversation to OpenRouter.
LESSON_CONTEXT_MAX_HISTORY_MESSAGES = 2
LESSON_CONTEXT_MAX_HISTORY_CHARS = 900
LESSON_CONTEXT_MAX_MESSAGE_CHARS = 450


class OpenRouterRequestError(RuntimeError):
    """An OpenRouter HTTP request failed with a known status code."""

    def __init__(self, status_code: int, detail: object):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"OpenRouter request failed ({status_code}): {detail}")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP_TITLE", "AI Language App"),
    }


def _is_lesson_system_message(message: dict[str, str]) -> bool:
    if message.get("role") != "system":
        return False

    content = str(message.get("content") or "")
    return (
        "You are the **TEACHING AI**" in content
        or "You are the **PRACTICE AI**" in content
    )


def _compact_lesson_messages(
    messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep lesson prompts under the small free-tier context budget.

    Backend lesson state, completed targets, current target, success criteria,
    language rules, and pedagogical rules stay in the system message. Only the
    two most recent stored conversation messages are sent as conversational
    memory, and those are capped by both per-message and total character
    budgets. The current user message remains untouched except for its normal
    validation upstream.
    """
    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
    ]

    if not any(_is_lesson_system_message(message) for message in system_messages):
        return messages

    non_system = [
        message
        for message in messages
        if message.get("role") != "system"
    ]

    recent = non_system[-LESSON_CONTEXT_MAX_HISTORY_MESSAGES:]
    compacted: list[dict[str, str]] = []
    remaining = LESSON_CONTEXT_MAX_HISTORY_CHARS

    for message in recent:
        content = str(message.get("content") or "").strip()
        if not content or remaining <= 0:
            continue

        limit = min(
            LESSON_CONTEXT_MAX_MESSAGE_CHARS,
            remaining,
        )

        if len(content) > limit:
            content = content[:limit].rstrip() + "…"

        compacted.append(
            {
                "role": message.get("role", "user"),
                "content": content,
            }
        )
        remaining -= len(content)

    return system_messages + compacted


def chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    response_format: dict | None = None,
) -> dict:
    import httpx

    messages = _compact_lesson_messages(messages)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "reasoning": {"enabled": False},
    }

    if response_format is not None:
        payload["response_format"] = response_format

    try:
        with httpx.Client(timeout=120.0) as http:
            response = http.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=_headers(),
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"OpenRouter network request failed: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise OpenRouterRequestError(response.status_code, detail)

    return response.json()


def stream_chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
):
    import json
    import httpx

    messages = _compact_lesson_messages(messages)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        "reasoning": {"enabled": False},
    }

    try:
        with httpx.Client(timeout=120.0) as http:
            with http.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=_headers(),
                json=payload,
            ) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    body = response.read()
                    try:
                        detail = json.loads(body.decode("utf-8"))
                    except (ValueError, UnicodeDecodeError):
                        detail = body.decode("utf-8", errors="replace")
                    raise OpenRouterRequestError(response.status_code, detail)

                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        return

                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    except httpx.HTTPError as exc:
        raise RuntimeError(f"OpenRouter network request failed: {exc}") from exc
