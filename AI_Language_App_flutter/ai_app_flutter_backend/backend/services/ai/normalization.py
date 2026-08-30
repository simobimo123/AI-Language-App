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
# Normalization
# =========================================================

def normalize_text(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    value = (
        value
        .strip()
        .casefold()
    )

    return value if value else None


def normalize_language(
    language: str,
) -> str:

    language = (
        language
        .strip()
        .lower()
    )

    if language not in SUPPORTED_LANGUAGES:

        raise ValueError(
            f"Unsupported language: {language}"
        )

    return language


def normalize_level(
    level: str | None,
) -> str | None:

    if level is None:
        return None

    level = (
        level
        .strip()
        .upper()
    )

    if level not in SUPPORTED_LEVELS:
        return None

    return level


def normalize_confidence(
    value,
) -> float:

    if value is None:
        return 0.5

    if isinstance(
        value,
        bool,
    ):

        return (
            1.0
            if value
            else 0.0
        )

    if isinstance(
        value,
        (int, float),
    ):

        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    text = (
        str(value)
        .strip()
        .lower()
    )

    mapping = {
        "very high": 0.95,
        "high": 0.90,
        "medium": 0.70,
        "moderate": 0.70,
        "low": 0.40,
        "very low": 0.20,
    }

    if text in mapping:
        return mapping[text]

    try:

        return max(
            0.0,
            min(
                1.0,
                float(text),
            ),
        )

    except ValueError:

        return 0.5

