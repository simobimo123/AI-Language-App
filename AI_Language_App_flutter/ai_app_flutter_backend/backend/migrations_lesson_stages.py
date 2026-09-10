from sqlalchemy import inspect, text

from database import engine


def ensure_lesson_stage_progress() -> None:
    """Create persistent state for the two active lesson stages."""
    with engine.begin() as connection:
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
                        teaching_status VARCHAR(20) NOT NULL DEFAULT 'available',
                        practice_status VARCHAR(20) NOT NULL DEFAULT 'locked',
                        teaching_started_at TIMESTAMP,
                        teaching_completed_at TIMESTAMP,
                        practice_started_at TIMESTAMP,
                        practice_completed_at TIMESTAMP,
                        teaching_conversation_id VARCHAR(120),
                        practice_conversation_id VARCHAR(120),
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_user_lesson_stage_progress UNIQUE (user_id, lesson_id)
                    )
                    """
                )
            )
            return

        columns = {
            column["name"]
            for column in inspect(connection).get_columns("user_lesson_stage_progress")
        }

        additions = {
            "teaching_status": "VARCHAR(20) NOT NULL DEFAULT 'available'",
            "practice_status": "VARCHAR(20) NOT NULL DEFAULT 'locked'",
            "teaching_started_at": "TIMESTAMP",
            "teaching_completed_at": "TIMESTAMP",
            "practice_started_at": "TIMESTAMP",
            "practice_completed_at": "TIMESTAMP",
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

        # The Learn stage was removed from the product. This migration also
        # cleans it up for databases that were created by an older version.
        for column in (
            "learn_status",
            "learn_started_at",
            "learn_completed_at",
        ):
            if column in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE user_lesson_stage_progress "
                        f"DROP COLUMN IF EXISTS {column}"
                    )
                )

        # Existing rows should begin directly with Teaching. Preserve any
        # completed Teaching/Practice state already stored in the database.
        connection.execute(
            text(
                """
                UPDATE user_lesson_stage_progress
                SET teaching_status = 'available'
                WHERE teaching_status = 'locked'
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE user_lesson_stage_progress
                SET practice_status = 'available'
                WHERE teaching_status = 'completed'
                  AND practice_status = 'locked'
                """
            )
        )


ensure_lesson_stage_progress()
