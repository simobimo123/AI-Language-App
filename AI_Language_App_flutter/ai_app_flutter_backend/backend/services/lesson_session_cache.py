from __future__ import annotations

"""Temporary in-memory sessions for lesson Teaching and Practice chats.

This module deliberately does not use SQLAlchemy, PostgreSQL, files, or any
other persistent storage. All lesson chat data stored here disappears when the
backend process restarts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class LessonChatMessage:
    """A single temporary lesson-chat message."""

    role: str
    content: str


@dataclass
class LessonChatSession:
    """Temporary state for one user's lesson stage."""

    user_id: int
    lesson_id: int
    stage: str
    conversation_id: str = field(default_factory=lambda: f"lesson_{uuid4()}")
    messages: list[LessonChatMessage] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def add_message(self, role: str, content: str) -> None:
        """Append a message and update the session timestamp."""
        self.messages.append(
            LessonChatMessage(
                role=role,
                content=content,
            )
        )
        self.updated_at = datetime.now(timezone.utc)


class LessonSessionCache:
    """Process-local cache for lesson chat sessions.

    The normal cache key includes the user, lesson, and stage, so Teaching and
    Practice can never accidentally share the same temporary conversation.
    A second conversation-ID index is kept so the existing lesson routes can
    retrieve the same temporary history without writing messages to the DB.
    """

    def __init__(self) -> None:
        self._sessions: dict[tuple[int, int, str], LessonChatSession] = {}
        self._conversation_index: dict[tuple[int, str], LessonChatSession] = {}
        self._lock = RLock()

    @staticmethod
    def _key(
        user_id: int,
        lesson_id: int,
        stage: str,
    ) -> tuple[int, int, str]:
        normalized_stage = stage.strip().lower()

        if normalized_stage not in {"teaching", "practice"}:
            raise ValueError(
                "Lesson stage must be 'teaching' or 'practice'."
            )

        return user_id, lesson_id, normalized_stage

    def get(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
    ) -> LessonChatSession | None:
        """Return an existing session without creating a new one."""
        key = self._key(user_id, lesson_id, stage)

        with self._lock:
            return self._sessions.get(key)

    def get_or_create(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
    ) -> tuple[LessonChatSession, bool]:
        """Return the session and whether it was newly created."""
        key = self._key(user_id, lesson_id, stage)

        with self._lock:
            session = self._sessions.get(key)

            if session is not None:
                session.updated_at = datetime.now(timezone.utc)
                return session, False

            session = LessonChatSession(
                user_id=user_id,
                lesson_id=lesson_id,
                stage=key[2],
            )
            self._sessions[key] = session
            self._conversation_index[
                (user_id, session.conversation_id)
            ] = session
            return session, True

    def register_conversation(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
        conversation_id: str,
    ) -> LessonChatSession:
        """Register an externally created lesson conversation ID."""
        key = self._key(user_id, lesson_id, stage)
        conversation_id = conversation_id.strip()

        if not conversation_id:
            raise ValueError("Conversation ID cannot be empty.")

        with self._lock:
            session = self._sessions.get(key)

            if session is not None:
                old_key = (user_id, session.conversation_id)
                if old_key != (user_id, conversation_id):
                    self._conversation_index.pop(old_key, None)
                session.conversation_id = conversation_id
                session.updated_at = datetime.now(timezone.utc)
            else:
                session = LessonChatSession(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    stage=key[2],
                    conversation_id=conversation_id,
                )
                self._sessions[key] = session

            self._conversation_index[
                (user_id, conversation_id)
            ] = session
            return session

    def get_by_conversation_id(
        self,
        user_id: int,
        conversation_id: str,
    ) -> LessonChatSession | None:
        """Return a temporary lesson session by its conversation ID."""
        conversation_id = conversation_id.strip()

        if not conversation_id:
            return None

        with self._lock:
            return self._conversation_index.get(
                (user_id, conversation_id)
            )

    def add_message(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
        role: str,
        content: str,
    ) -> LessonChatSession:
        """Create the temporary session if necessary and append a message."""
        session, _ = self.get_or_create(
            user_id=user_id,
            lesson_id=lesson_id,
            stage=stage,
        )

        with self._lock:
            session.add_message(role=role, content=content)
            return session

    def add_message_by_conversation_id(
        self,
        user_id: int,
        conversation_id: str,
        role: str,
        content: str,
    ) -> LessonChatSession:
        """Append to an existing temporary lesson conversation.

        This fallback also supports the current lesson route while it still
        generates the conversation ID itself. No lesson message is persisted.
        """
        conversation_id = conversation_id.strip()

        if not conversation_id.startswith("lesson_"):
            raise ValueError("Not a lesson conversation ID.")

        with self._lock:
            session = self._conversation_index.get(
                (user_id, conversation_id)
            )

            if session is None:
                stage = (
                    "practice"
                    if conversation_id.startswith("lesson_practice_")
                    else "teaching"
                )
                session = LessonChatSession(
                    user_id=user_id,
                    lesson_id=0,
                    stage=stage,
                    conversation_id=conversation_id,
                )
                self._conversation_index[
                    (user_id, conversation_id)
                ] = session

            session.add_message(role=role, content=content)
            return session

    def messages(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
    ) -> list[LessonChatMessage]:
        """Return a copy of the current temporary message history."""
        session = self.get(
            user_id=user_id,
            lesson_id=lesson_id,
            stage=stage,
        )

        if session is None:
            return []

        with self._lock:
            return list(session.messages)

    def clear(
        self,
        user_id: int,
        lesson_id: int,
        stage: str,
    ) -> bool:
        """Remove one temporary lesson session from memory."""
        key = self._key(user_id, lesson_id, stage)

        with self._lock:
            session = self._sessions.pop(key, None)
            if session is None:
                return False

            self._conversation_index.pop(
                (user_id, session.conversation_id),
                None,
            )
            return True

    def clear_user(self, user_id: int) -> int:
        """Remove all temporary lesson sessions belonging to one user."""
        with self._lock:
            keys = [
                key
                for key in self._sessions
                if key[0] == user_id
            ]

            for key in keys:
                session = self._sessions.pop(key)
                self._conversation_index.pop(
                    (user_id, session.conversation_id),
                    None,
                )

            return len(keys)


# One process-local cache shared by the lesson AI routes.
lesson_session_cache = LessonSessionCache()
