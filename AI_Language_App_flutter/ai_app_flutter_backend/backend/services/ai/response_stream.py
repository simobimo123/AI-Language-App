import json
import logging
from typing import Generator

from google.genai import types
from sqlalchemy.orm import Session

from services.ai.usage import (
    DAILY_AI_LIMIT,
    extract_token_usage,
    get_current_usage,
    record_api_usage,
)
from services.ai.conversation import (
    cleanup_old_conversation_messages,
    save_conversation_message,
)
from services.ai.client import AI_MODEL, client


logger = logging.getLogger(__name__)


def sse_event(payload: dict) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def stream_gemini_response(
    request,
    current_user,
    db: Session,
    learning_context: str,
    contents: list[types.Content],
    max_output_tokens: int,
    max_conversation_messages: int,
    classification_decision: str,
) -> Generator[str, None, None]:
    logger.info(
        "Gemini chat request user_id=%s model=%s classification=%s",
        current_user.id,
        AI_MODEL,
        classification_decision,
    )

    full_response = ""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    try:
        response_stream = client.models.generate_content_stream(
            model=AI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                system_instruction=learning_context,
            ),
        )

        for chunk in response_stream:
            chunk_text = getattr(chunk, "text", None)
            chunk_prompt_tokens, chunk_completion_tokens, chunk_total_tokens = (
                extract_token_usage(chunk)
            )
            prompt_tokens = max(prompt_tokens, chunk_prompt_tokens)
            completion_tokens = max(completion_tokens, chunk_completion_tokens)
            total_tokens = max(total_tokens, chunk_total_tokens)

            if not chunk_text:
                continue

            full_response += chunk_text
            yield sse_event({"type": "chunk", "text": chunk_text})

        if not full_response:
            raise RuntimeError("Gemini returned an empty response.")

        save_conversation_message(
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            role="user",
            content=request.message,
            db=db,
        )
        save_conversation_message(
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            role="model",
            content=full_response,
            db=db,
        )
        cleanup_old_conversation_messages(
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            max_messages=max_conversation_messages,
            db=db,
        )
        db.commit()

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            db=db,
        )
        usage = get_current_usage(user_id=current_user.id, db=db)
        yield sse_event(
            {
                "type": "done",
                "daily_limit": DAILY_AI_LIMIT,
                "daily_used": usage.request_count,
                "daily_remaining": max(
                    0,
                    DAILY_AI_LIMIT - usage.request_count,
                ),
            }
        )
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Gemini streaming failed user_id=%s: %s",
            current_user.id,
            exc,
        )
        yield sse_event(
            {
                "type": "error",
                "message": "AI service is temporarily unavailable.",
            }
        )


