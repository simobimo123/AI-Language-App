from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)



class Base(DeclarativeBase):
    pass


# =========================================================
# Shared constants
# =========================================================

SUPPORTED_LANGUAGE_CODES = (
    "ar",
    "de",
    "en",
    "es",
    "fr",
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
)


SUPPORTED_CEFR_LEVELS = (
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
)
