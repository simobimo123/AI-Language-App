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
# AI MODELS
# ============================================================================

AI_MODEL = os.getenv(
    "OPENROUTER_MAIN_MODEL",
    "minimax/minimax-m2.7:free",
).strip()

AI_CLASSIFIER_MODEL = os.getenv(
    "OPENROUTER_CLASSIFIER_MODEL",
    AI_MODEL,
).strip()

if not AI_MODEL:
    raise RuntimeError(
        "OPENROUTER_MAIN_MODEL is empty in the .env file"
    )

if not AI_CLASSIFIER_MODEL:
    raise RuntimeError(
        "OPENROUTER_CLASSIFIER_MODEL is empty in the .env file"
    )


# OpenRouter exposes reasoning controls for models that support them.
# "none" is intentionally the default for this app: lesson decisions are
# simple and should not spend output tokens on hidden reasoning.
OPENROUTER_REASONING_EFFORT = os.getenv(
    "OPENROUTER_REASONING_EFFORT",
    "none",
).strip().lower()

if OPENROUTER_REASONING_EFFORT not in {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
}:
    raise RuntimeError(
        "OPENROUTER_REASONING_EFFORT must be one of: "
        "none, minimal, low, medium, high, xhigh"
    )


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

    Reasoning is explicitly controlled so simple application decisions do not
    silently consume most of the output budget.
    """

    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "reasoning": {
            "effort": OPENROUTER_REASONING_EFFORT,
        },
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

    The lesson provider intentionally buffers lesson responses so the backend
    can process the internal LESSON_PROGRESS marker safely.
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
        "reasoning": {
            "effort": OPENROUTER_REASONING_EFFORT,
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
        raise RuntimeError(
            f"OpenRouter network request failed: {exc}"
        ) from exc
