import os

from dotenv import load_dotenv


load_dotenv()


OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured in the .env file"
    )


OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
).rstrip("/")


# ============================================================================
# AI MODEL
# ============================================================================

# Single AI model for the entire application.
#
# Chat
# Classification
# Vocabulary enrichment
# Translation
# Lesson tutoring
# Hints
# Lesson generation
#
# All use MiniMax through OpenRouter.
AI_MODEL = "minimax/minimax-m2.7:free"

AI_CLASSIFIER_MODEL = AI_MODEL


# ============================================================================
# ERRORS
# ============================================================================


class OpenRouterRequestError(RuntimeError):
    """An OpenRouter HTTP request failed with a known status code."""

    def __init__(
        self,
        status_code: int,
        detail: object,
    ):
        self.status_code = status_code
        self.detail = detail

        super().__init__(
            f"OpenRouter request failed "
            f"({status_code}): {detail}"
        )


# ============================================================================
# HEADERS
# ============================================================================


def _headers() -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
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


# ============================================================================
# NON-STREAMING CHAT
# ============================================================================


def chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    response_format: dict | None = None,
) -> dict:
    """
    Send one non-streaming request to OpenRouter.

    Reasoning configuration is intentionally left to the model/endpoint.

    MiniMax reasoning is not disabled.
    """

    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    if response_format is not None:
        payload["response_format"] = response_format

    try:
        with httpx.Client(
            timeout=120.0
        ) as http:
            response = http.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=_headers(),
                json=payload,
            )

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"OpenRouter network request failed: {exc}"
        ) from exc

    if (
        response.status_code < 200
        or response.status_code >= 300
    ):
        try:
            detail = response.json()

        except ValueError:
            detail = response.text

        raise OpenRouterRequestError(
            response.status_code,
            detail,
        )

    return response.json()


# ============================================================================
# STREAMING CHAT
# ============================================================================


def stream_chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
):
    """
    Yield decoded OpenRouter SSE payloads.

    The lesson provider intentionally buffers lesson responses so the
    backend can process the internal LESSON_PROGRESS marker safely.
    """

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
        with httpx.Client(
            timeout=120.0
        ) as http:

            with http.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=_headers(),
                json=payload,
            ) as response:

                if (
                    response.status_code < 200
                    or response.status_code >= 300
                ):
                    body = response.read()

                    try:
                        detail = json.loads(
                            body.decode("utf-8")
                        )

                    except (
                        ValueError,
                        UnicodeDecodeError,
                    ):
                        detail = body.decode(
                            "utf-8",
                            errors="replace",
                        )

                    raise OpenRouterRequestError(
                        response.status_code,
                        detail,
                    )

                for line in response.iter_lines():

                    if not line:
                        continue

                    # SSE comments / keep-alives.
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()

                    if data == "[DONE]":
                        return

                    try:
                        yield json.loads(data)

                    except json.JSONDecodeError:
                        # Ignore malformed/non-JSON SSE lines rather than
                        # terminating an otherwise valid stream.
                        continue

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"OpenRouter network request failed: {exc}"
        ) from exc