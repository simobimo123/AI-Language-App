from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal
import migrations_learning_bank  # noqa: F401

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.words import router as words_router
from routers.word_lookup import router as word_lookup_router
from routers.translation import router as translation_router

from routers.learning_profiles import (
    router as learning_router,
)

from routers.learning_path import (
    router as learning_path_router,
    seed_learning_content,
)

from routers.ai import (
    router as ai_router,
)

from routers.lesson_ai import (
    router as lesson_ai_router,
)

from routers.lesson_hint import (
    router as lesson_hint_router,
)

from routers.lesson_assessment import (
    router as lesson_assessment_router,
)

from routers.placement_test import (
    router as placement_router,
)

from routers.vocabulary import (
    router as vocabulary_router,
)

from routers.stats import (
    router as stats_router,
)

from routers.lesson_content import (
    router as lesson_content_router,
)

from routers.lesson_preview import (
    router as lesson_preview_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()

    try:
        seed_learning_content(db)
    finally:
        db.close()

    yield


app = FastAPI(
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Hello from my backend"
    }


# =========================================================
# Routers
# =========================================================

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(words_router)
app.include_router(word_lookup_router)
app.include_router(translation_router)
app.include_router(learning_router)
app.include_router(learning_path_router)
app.include_router(ai_router)
app.include_router(lesson_ai_router)
app.include_router(lesson_hint_router)
app.include_router(lesson_assessment_router)
app.include_router(placement_router)
app.include_router(vocabulary_router)
app.include_router(stats_router)
app.include_router(lesson_content_router)
app.include_router(lesson_preview_router)

# python -m uvicorn main:app --reload --host 0.0.0.0
