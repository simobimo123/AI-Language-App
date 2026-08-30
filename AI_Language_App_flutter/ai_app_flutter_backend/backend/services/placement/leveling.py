from fastapi import HTTPException

from services.placement.config import ALL_LEVELS, LEVELS


def normalize_language(
    language: str,
) -> str:
    return (
        language
        .strip()
        .lower()
    )


def normalize_level(
    level: str,
) -> str:
    normalized = (
        level
        .strip()
        .upper()
    )

    if normalized not in ALL_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid level '{normalized}'."
            ),
        )

    return normalized


def calculate_previous_level(
    level: str,
) -> str:

    if level == "A1":
        return "PRE_A1"

    index = LEVELS.index(
        level
    )

    if index == 0:
        return "PRE_A1"

    return LEVELS[
        index - 1
    ]


def calculate_next_level(
    level: str,
) -> str | None:

    index = LEVELS.index(
        level
    )

    if index >= len(LEVELS) - 1:
        return None

    return LEVELS[
        index + 1
    ]
