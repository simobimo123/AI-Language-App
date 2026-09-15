import os
import re
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
    raise RuntimeError("OPENROUTER_MAIN_MODEL is not configured in the backend .env file")

if not AI_CLASSIFIER_MODEL:
    raise RuntimeError("OPENROUTER_CLASSIFIER_MODEL is not configured in the backend .env file")


LESSON_CONTEXT_MAX_HISTORY_MESSAGES = 1
LESSON_CONTEXT_MAX_HISTORY_CHARS = 600
LESSON_CONTEXT_MAX_MESSAGE_CHARS = 600


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


def _extract_block(text: str, heading: str, next_heading: str | None = None) -> str:
    if next_heading:
        pattern = rf"({re.escape(heading)}.*?)(?=\n\n{re.escape(next_heading)}|\Z)"
    else:
        pattern = rf"({re.escape(heading)}.*)"

    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def _compact_teaching_system_prompt(system: str) -> str:
    language_match = re.search(
        r"\*\*LANGUAGE\*\*:\s*([^\n]+)\s*\n\*\*LEVEL\*\*:\s*([^\n]+)",
        system,
    )
    target_order_match = re.search(
        r'\"target_order\"\s*:\s*(\d+|null)',
        system,
    )

    language = language_match.group(1).strip() if language_match else "unknown"
    level = language_match.group(2).strip() if language_match else "unknown"
    target_order = target_order_match.group(1) if target_order_match else "null"

    current = _extract_block(
        system,
        "**CURRENT TARGET**:",
        "**NEXT TARGET**:",
    )
    next_target = _extract_block(
        system,
        "**NEXT TARGET**:",
        "**CORE PEDAGOGICAL SEQUENCE",
    )

    return f"""You are the TEACHING AI for a {level} language lesson.
LANGUAGE: {language}
{current or '**CURRENT TARGET**: none'}
{next_target or '**NEXT TARGET**: none'}

RULES:
- TEACH meaning/form first; MODEL one short correct example; then ASK one learner prompt.
- Evaluate only the learner's latest message for the current target.
- Meaningful error: show `wrong → correct`, give one short reason, then ask for retry.
- Do not advance until the current target clearly satisfies its success criteria.
- Once complete, do not require the same target again; teach/model the next target and give one prompt.
- Accept natural correct alternatives.
- Use the backend-selected explanation language for teacher explanations/corrections; use the learning language for targets/examples.
- Keep replies short, one prompt only, no stories or invented learner information.
- Red `"text"` and green `*text*` may mark corrections.

OUTPUT: ONLY valid JSON:
{{"reply":"learner-facing text","target_completed":false,"target_order":{target_order},"stage_completed":false}}
stage_completed=true only when the current target is complete and it is the final required target.
""".strip()


def _compact_practice_system_prompt(system: str) -> str:
    language_match = re.search(
        r"\*\*LANGUAGE\*\*:\s*([^\n]+)\s*\n\*\*LEVEL\*\*:\s*([^\n]+)",
        system,
    )
    language = language_match.group(1).strip() if language_match else "unknown"
    level = language_match.group(2).strip() if language_match else "unknown"

    scenario = _extract_block(system, "**PRACTICE SCENARIO**:")
    targets = _extract_block(system, "**LESSON TARGETS**:", "**PRACTICE SCENARIO**:")

    return f"""You are the PRACTICE AI for a {level} lesson.
LANGUAGE: {language}
TARGETS: {targets[:500]}
SCENARIO: {scenario[:300]}

RULES:
- Natural conversation partner, not formal teacher.
- Respond to the learner's actual message; never invent the learner's answer/info.
- Ask at most one natural question at a time.
- Practice targets naturally; do not force a checklist.
- Correct meaningful errors briefly; keep replies short and level-appropriate.
- Output only learner-facing conversation.
""".strip()


def _compact_lesson_system(system: str) -> str:
    if "You are the **TEACHING AI**" in system:
        return _compact_teaching_system_prompt(system)
    if "You are the **PRACTICE AI**" in system:
        return _compact_practice_system_prompt(system)
    return system


def _compact_lesson_messages(
    messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Send only compact lesson state plus the current learner message."""
    lesson_system = next(
        (
            dict(message)
            for message in messages
            if _is_lesson_system_message(message)
        ),
        None,
    )

    if lesson_system is None:
        return messages

    lesson_system["content"] = _compact_lesson_system(
        str(lesson_system.get("content") or "")
    )

    non_system = [
        message
        for message in messages
        if message.get("role") != "system"
    ]

    recent = non_system[-LESSON_CONTEXT_MAX_HISTORY_MESSAGES:]
    compacted: list[dict[str, str]] = []

    for message in recent:
        content = str(message.get("content") or "").strip()
        if not content:
            continue

        if len(content) > LESSON_CONTEXT_MAX_MESSAGE_CHARS:
            content = content[:LESSON_CONTEXT_MAX_MESSAGE_CHARS].rstrip() + "…"

        compacted.append(
            {
                "role": message.get("role", "user"),
                "content": content,
            }
        )

    return [lesson_system] + compacted


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
