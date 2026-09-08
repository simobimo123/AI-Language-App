from pathlib import Path
import os

from dotenv import load_dotenv


# Load the backend .env independently of the process working directory.
# This prevents OpenRouter credentials from disappearing when Uvicorn is
# started from a different folder.
_THIS_FILE = Path(__file__).resolve()
_BACKEND_ROOT = _THIS_FILE.parents[2]
_APP_ROOT = _THIS_FILE.parents[3]

for _env_path in (
    _BACKEND_ROOT / ".env",
    _APP_ROOT / ".env",
):
    if _env_path.is_file():
        load_dotenv(dotenv_path=_env_path, override=False)

# Also keep normal environment variables supported (for deployment/CI).
load_dotenv(override=False)


OPENROUTER_API_KEY = (os.getenv("OPENROUTER_API_KEY") or "").strip()

# Avoid accidentally sending an empty/whitespace Authorization header.
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured. "
        "Set it in the backend .env file or as an environment variable."
    )


OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
).strip().rstrip("/")


# ============================================================================
# AI MODELS
# ============================================================================

# The application uses separate OpenRouter models for different workloads.
# Keep these values in .env so changing a provider/model does not require a
# source-code change or redeploy of the Python module itself.
#
# Main model:
#   Chat, lesson tutoring, lesson generation and other general AI tasks.
# Classifier model:
#   Classification-specific tasks.
#
# Translation models are intentionally not defined here because their callers
# may use dedicated translation configuration.
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
    # Construct the Authorization header at request time so every request
    # uses the same validated credential and no request can omit it.
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

    Reasoning is explicitly disabled for the request. The model still
    generates its normal final answer without spending the output budget on
    reasoning tokens.
    """

    import httpx

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "reasoning": {
            "enabled": False,
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

    The lesson provider intentionally buffers lesson responses so the
    backend can process the internal LESSON_PROGRESS marker safely.

    Reasoning is explicitly disabled for the request.
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
            "enabled": False,
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
