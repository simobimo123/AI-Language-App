from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.words import router as words_router
from routers.learning_profiles import (
    router as learning_router,
)
from routers.learning_path import (
    router as learning_path_router,
    seed_learning_content,
)
from routers.ai import router as ai_router
from routers.placement_test import (
    router as placement_router,
)
from routers.vocabulary import (
    router as vocabulary_router,
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


app.include_router(users_router)
app.include_router(auth_router)
app.include_router(words_router)
app.include_router(learning_router)
app.include_router(learning_path_router)
app.include_router(ai_router)
app.include_router(placement_router)
app.include_router(vocabulary_router)


# python -m uvicorn main:app --reload --host 0.0.0.0