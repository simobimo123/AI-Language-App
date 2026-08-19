from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    native_language: str = Field(default="ar", min_length=2, max_length=10)
    learning_language: str = Field(default="en", min_length=2, max_length=10)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    native_language: str = Field(min_length=2, max_length=10)
    learning_language: str = Field(min_length=2, max_length=10)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    native_language: str
    learning_language: str

    class Config:
        from_attributes = True


class WordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=255)
    translation: str = Field(min_length=1, max_length=255)


class WordResponse(BaseModel):
    id: int
    word: str
    translation: str
    learned: bool
    user_id: int

    class Config:
        from_attributes = True
