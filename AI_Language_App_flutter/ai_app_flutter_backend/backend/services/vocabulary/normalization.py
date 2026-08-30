from fastapi import HTTPException


# =========================================================
# Constants
# =========================================================

SUPPORTED_LANGUAGES = {
    "ar",
    "de",
    "en",
    "es",
    "fa",
    "fr",
    "hi",
    "id",
    "it",
    "ja",
    "ko",
    "nl",
    "pl",
    "pt",
    "ru",
    "th",
    "tr",
    "uk",
    "vi",
    "zh",
}

SUPPORTED_LEVELS = {
    "PRE_A1",
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
}


# =========================================================
# Normalization helpers
# =========================================================

def normalize_language(
    language: str,
) -> str:

    normalized = language.strip().lower()

    if normalized not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported language '{normalized}'. "
                f"Supported languages: "
                f"{', '.join(sorted(SUPPORTED_LANGUAGES))}"
            ),
        )

    return normalized


def normalize_level(
    level: str,
) -> str:

    normalized = level.strip().upper()

    if normalized not in SUPPORTED_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported level '{normalized}'. "
                f"Supported levels: "
                f"{', '.join(sorted(SUPPORTED_LEVELS))}"
            ),
        )

    return normalized


def normalize_form(
    form: str,
) -> str:

    return " ".join(
        form.strip().casefold().split()
    )


def normalize_lemma(
    lemma: str,
) -> str:

    return " ".join(
        lemma.strip().casefold().split()
    )


def clean_optional_text(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    value = value.strip()

    return value if value else None
