from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal
import migrations_learning_bank  # noqa: F401
import migrations_lesson_progress  # noqa: F401

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

from routers.lesson_translation_check import (
    router as lesson_translation_check_router,
)

from routers.placement_test import (
    router as placement_router,
)