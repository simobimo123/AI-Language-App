from sqlalchemy import inspect, text

from database import engine


def ensure_lesson_stage_progress() -> None:
    """Create persistent per-user state for the three lesson stages."""
    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        if "user_lesson_stage_progress" not in tables:
            connection.execute(
                text(
                    """
                    CREATE TABLE user_lesson_stage_progress (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        learning_profile_id INTEGER NOT NULL REFERENCES learning_profiles(id) ON DELETE CASCADE,
                        lesson_id INTEGER NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
                        learn_status VARCHAR(20) NOT NULL DEFAULT 'available',
                        teaching_status VARCHAR(20) NOT NULL DEFAULT 'locked',
                        practice_status VARCHAR(20) NOT NULL DEFAULT 'locked',
                        teaching_conversation_id VARCHAR(120),
                        practice_conversation_id VARCHAR(120),
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_user_lesson_stage_progress UNIQUE (user_id, lesson_id)
                    )
                    """
                )
            )
            connection.commit()
            return

        columns = {
            column["name"]
            for column in inspector.get_columns("user_lesson_stage_progress")
        }

        additions = {
            "learn_status": "VARCHAR(20) NOT NULL DEFAULT 'available'",
            "teaching_status": "VARCHAR(20) NOT NULL DEFAULT 'locked'",
            "practice_status": "VARCHAR(20) NOT NULL DEFAULT 'locked'",
            "teaching_conversation_id": "VARCHAR(120)",
            "practice_conversation_id": "VARCHAR(120)",
            "updated_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }

        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE user_lesson_stage_progress "
                        f"ADD COLUMN {name} {definition}"
                    )
                )

        connection.commit()


ensure_lesson_stage_progress()
