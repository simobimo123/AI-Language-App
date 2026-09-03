from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models import AIConversationMessage


def get_conversation_history(
    user_id: int,
    conversation_id: str | None,
    max_messages: int,
    db: Session,
) -> list[AIConversationMessage]:
    query = select(AIConversationMessage).where(
        AIConversationMessage.user_id == user_id,
    )

    if conversation_id:
        query = query.where(
            AIConversationMessage.conversation_id == conversation_id,
        )

    messages = (
        db.execute(
            query.order_by(
                AIConversationMessage.created_at.desc(),
                AIConversationMessage.id.desc(),
            ).limit(max_messages)
        )
        .scalars()
        .all()
    )
    messages.reverse()
    return messages


def build_chat_messages(
    history: list[AIConversationMessage],
    current_message: str,
    vocabulary_context: str | None,
) -> list[dict[str, str]]:
    """Convert database conversation rows to OpenAI-compatible messages."""
    messages: list[dict[str, str]] = []

    for message in history:
        role = "assistant" if message.role == "model" else message.role

        if role not in {"user", "assistant", "system"}:
            role = "assistant"

        messages.append(
            {
                "role": role,
                "content": message.content,
            }
        )

    current_text = current_message

    if vocabulary_context:
        current_text = (
            "VOCABULARY DATABASE DATA\n\n"
            + vocabulary_context
            + "\n\nUSER REQUEST\n"
            + current_message
        )

    messages.append(
        {
            "role": "user",
            "content": current_text,
        }
    )

    return messages


# Backward-compatible name used by the existing router.
build_gemini_contents = build_chat_messages


def save_conversation_message(
    user_id: int,
    conversation_id: str | None,
    role: str,
    content: str,
    db: Session,
) -> None:
    db.add(
        AIConversationMessage(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
    )


def cleanup_old_conversation_messages(
    user_id: int,
    conversation_id: str | None,
    max_messages: int,
    db: Session,
) -> None:
    query = select(AIConversationMessage.id).where(
        AIConversationMessage.user_id == user_id,
    )

    if conversation_id:
        query = query.where(
            AIConversationMessage.conversation_id == conversation_id,
        )

    message_ids = (
        db.execute(
            query.order_by(
                AIConversationMessage.created_at.desc(),
                AIConversationMessage.id.desc(),
            ).offset(max_messages)
        )
        .scalars()
        .all()
    )

    if message_ids:
        db.execute(
            delete(AIConversationMessage).where(
                AIConversationMessage.id.in_(message_ids)
            )
        )
