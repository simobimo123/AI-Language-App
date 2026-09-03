import logging
import uuid

from sqlalchemy.orm import Session

from services.ai.client import AI_MODEL, stream_chat_completion
from services.ai.usage import (
    DAILY_AI_LIMIT,
    get_current_usage,
    record_api_usage,
)
from services.ai.conversation import (
    cleanup_old_conversation_messages,
    save_conversation_message,
)


logger = logging.getLogger(__name__)


def sse_event(payload: dict) -> str:
    import json

    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def stream_openrouter_response(
    request,
    current_user,
    db: Session,
    learning_context: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    max_conversation_messages: int,
    classification_decision: str,
):
    logger.info(
        "OpenRouter chat request user_id=%s model=%s classification=%s",
        current_user.id,
        AI_MODEL,
        classification_decision,
    )

    full_response = ""
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    # OpenRouter does not create application conversation IDs for us.
    # Generate one server-side so the existing Flutter conversation flow
    # continues to work even when the first request has no ID yet.
    conversation_id = request.conversation_id or str(uuid.uuid4())

    yield sse_event(
        {
            "type": "conversation",
            "conversation_id": conversation_id,
        }
    )

    # The system instruction is sent separately from the stored conversation
    # so it is never persisted as a user/model message.
    openrouter_messages = [
        {
            "role": "system",
            "content": learning_context,
        },
        *messages,
    ]

    try:
        for chunk in stream_chat_completion(
            model=AI_MODEL,
            messages=openrouter_messages,
            max_tokens=max_output_tokens,
        ):
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                chunk_text = delta.get("content")

                if chunk_text:
                    full_response += chunk_text
                    yield sse_event(
                        {
                            "type": "chunk",
                            "text": chunk_text,
                        }
                    )

            usage = chunk.get("usage")
            if isinstance(usage, dict):
                prompt_tokens = max(
                    prompt_tokens,
                    int(usage.get("prompt_tokens") or 0),
                )
                completion_tokens = max(
                    completion_tokens,
                    int(usage.get("completion_tokens") or 0),
                )
                total_tokens = max(
                    total_tokens,
                    int(usage.get("total_tokens") or 0),
                )

        if not full_response:
            raise RuntimeError("OpenRouter returned an empty response.")

        save_conversation_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
            role="user",
            content=request.message,
            db=db,
        )
        save_conversation_message(
            user_id=current_user.id,
            conversation_id=conversation_id,
            role="model",
            content=full_response,
            db=db,
        )
        cleanup_old_conversation_messages(
            user_id=current_user.id,
            conversation_id=conversation_id,
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

        usage = get_current_usage(
            user_id=current_user.id,
            db=db,
        )

        yield sse_event(
            {
                "type": "done",
                "conversation_id": conversation_id,
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
            "OpenRouter streaming failed user_id=%s: %s",
            current_user.id,
            exc,
        )

        yield sse_event(
            {
                "type": "error",
                "message": "AI service is temporarily unavailable.",
            }
        )
