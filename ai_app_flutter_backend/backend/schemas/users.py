from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import (
    ENRICHMENT_STATUS_PATTERN,
    LANGUAGE_CODE_PATTERN,
    LEVEL_PATTERN,
)

# =========================================================
# User
# =========================================================

class UserCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    native_language: str = Field(
        default="ar",
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    learning_language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    learning_level: str = Field(
        default="A1",
        min_length=2,
        max_length=10,
        pattern=LEVEL_PATTERN,
    )


class UserLogin(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


# =========================================================
# Google Login
# =========================================================

class GoogleLogin(BaseModel):
    id_token: str = Field(
        min_length=1,
    )


class UserUpdate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    native_language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )

    learning_language: str = Field(
        min_length=2,
        max_length=10,
        pattern=LANGUAGE_CODE_PATTERN,
    )


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    native_language: str
    learning_language: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# Learning Profile
# =========================================================

