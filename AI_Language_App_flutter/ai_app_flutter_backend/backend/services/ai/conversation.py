from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models import AIConversationMessage
from services.lesson_session_cache import lesson_session_cache

LESSON_CONVERSATION_PREFIX = "lesson_"


def get_conversation_history(
    user_id: int,
    conversation_id: str | None,
    max_messages: int,
    db: Session,
) -> list:
    """Return conversation history, using RAM-only storage for lesson chats."""
    is_lesson_conversation = bool(
        conversation_id
        and conversation_id.startswith(LESSON_CONVERSATION_PREFIX)
    )

    if is_lesson_conversation:
        session = lesson_session_cache.get_by_conversation_id(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        if session is None:
            return []

        return list(session.messages)

    query = select(AIConversationMessage).where(
        AIConversationMessage.user_id == user_id,
    )

    if conversation_id:
        query = query.where(
            AIConversationMessage.conversation_id == conversation_id
        )

    query = query.order_by(
        AIConversationMessage.created_at.asc(),
        AIConversationMessage.id.asc(),
    ).limit(max_messages)

    return db.execute(query).scalars().all()


def build_chat_messages(
    history: list[AIConversationMessage],
    current_message: str,
    vocabulary_context: str | None,
) -> list[dict[str, str]]:
    """Convert conversation rows to OpenAI-compatible messages."""
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


def save_conversation_message(
    user_id: int,
    conversation_id: str | None,
    role: str,
    content: str,
    db: Session,
) -> None:
    """Store lesson messages in RAM and all other chats in the DB."""
    if conversation_id and conversation_id.startswith(LESSON_CONVERSATION_PREFIX):
        lesson_session_cache.add_message_by_conversation_id(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        return

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
    """Trim non-lesson chats; lesson chats are RAM-only and need no cleanup."""
    if conversation_id and conversation_id.startswith(LESSON_CONVERSATION_PREFIX):
        return

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
