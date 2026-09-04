import os

from dotenv import load_dotenv


load_dotenv()


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured in the .env file"
    )


OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
).rstrip("/")

# Single AI model for the entire application.
# Keep this centralized so chat, classification, vocabulary enrichment,
# translation, lesson tutoring, hints, and lesson generation all use MiniMax.
AI_MODEL = "minimax/minimax-m2.7:free"
AI_CLASSIFIER_MODEL = AI_MODEL


class OpenRouterRequestError(RuntimeError):
    """An OpenRouter HTTP request failed with a known status code."""

    def __init__(self, status_code: int, detail: object):
        self.status_code = status_code
        self.detail = detail
        super().__init__(
            f"OpenRouter request failed ({status_code}): {detail}"
        )


# OpenRouter exposes an OpenAI-compatible Chat Completions API.
# Keeping the HTTP layer here makes the rest of the AI service independent
# from the model vendor while ensuring the application uses the single
# centrally selected MiniMax model above.
def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv(
            "OPENROUTER_HTTP_REFERER",
            "http://localhost",
        ),
        "X-Title": os.getenv(
            "OPENROUTER_APP_TITLE",
            "AI Language App",
        ),
    }


def chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    response_format: dict | None = None,
) -> dict:
    """Send one non-streaming request to OpenRouter."""
    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
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
    """Yield decoded OpenRouter SSE payloads for a streaming request."""
    import json
    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {
            "include_usage": True,
        },
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
                    if not line:
                        continue

                    if not line.startswith("data:"):
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
