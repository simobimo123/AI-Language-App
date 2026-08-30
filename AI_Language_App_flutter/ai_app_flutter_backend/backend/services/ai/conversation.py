from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from google.genai import types

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


def build_gemini_contents(
    history: list[AIConversationMessage],
    current_message: str,
    vocabulary_context: str | None,
) -> list[types.Content]:
    contents: list[types.Content] = []

    for message in history:
        contents.append(
            types.Content(
                role=message.role,
                parts=[types.Part(text=message.content)],
            )
        )

    current_text = current_message
    if vocabulary_context:
        current_text = (
            "VOCABULARY DATABASE DATA\n\n"
            + vocabulary_context
            + "\n\nUSER REQUEST\n"
            + current_message
        )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=current_text)],
        )
    )
    return contents


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


