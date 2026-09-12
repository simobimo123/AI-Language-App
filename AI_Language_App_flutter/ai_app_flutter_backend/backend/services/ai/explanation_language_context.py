from contextvars import ContextVar


# Request-scoped Teaching AI explanation-language context.
# Format: "mode|native_language|learning_language"
# Example: "native|ar|de"
_EXPLANATION_CONTEXT: ContextVar[str] = ContextVar(
    "lesson_explanation_language_context",
    default="",
)


def set_explanation_language_context(
    *,
    mode: str,
    native_language: str,
    learning_language: str,
) -> None:
    normalized_mode = (
        mode.strip().lower()
        if mode
        else "native"
    )

    if normalized_mode not in {"native", "learning"}:
        normalized_mode = "native"

    _EXPLANATION_CONTEXT.set(
        f"{normalized_mode}|{native_language.strip().lower()}|{learning_language.strip().lower()}"
    )


def get_explanation_language_context() -> tuple[str, str, str] | None:
    raw = _EXPLANATION_CONTEXT.get().strip()

    if not raw:
        return None

    parts = raw.split("|", 2)

    if len(parts) != 3:
        return None

    mode, native_language, learning_language = (
        part.strip().lower()
        for part in parts
    )

    if mode not in {"native", "learning"}:
        return None

    if not native_language or not learning_language:
        return None

    return mode, native_language, learning_language
