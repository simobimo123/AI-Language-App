from fastapi import FastAPI

from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.words import router as words_router


app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "Hello from my backend"
    }


app.include_router(users_router)
app.include_router(auth_router)
app.include_router(words_router)


# uvicorn main:app --reload