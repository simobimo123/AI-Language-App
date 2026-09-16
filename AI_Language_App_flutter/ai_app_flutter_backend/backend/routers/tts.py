"""Authenticated local TTS endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from models import User
from routers.auth import get_current_user
from services.tts.manager import TTSManager


router = APIRouter(prefix="/ai/tts", tags=["AI TTS"])
_tts_manager = TTSManager()


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    learning_language: str | None = Field(default=None, min_length=2, max_length=10)
    native_language: str | None = Field(default=None, min_length=2, max_length=10)
    gender: str | None = Field(default=None, pattern="^(male|female)$")


@router.post("/")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    learning_language = request.learning_language or current_user.learning_language
    native_language = request.native_language or current_user.native_language

    try:
        audio, segments = await run_in_threadpool(
            _tts_manager.synthesize,
            request.text,
            learning_language=learning_language,
            native_language=native_language,
            gender=request.gender,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local TTS is temporarily unavailable.",
        ) from exc

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-TTS-Segments": str(len(segments)),
        },
    )
