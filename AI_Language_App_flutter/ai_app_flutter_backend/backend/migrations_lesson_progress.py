from sqlalchemy import inspect, text

from database import engine


def ensure_lesson_practice_state() -> None:
    """Add compact per-lesson sentence-practice state to existing databases."""
    with engine.connect() as connection:
        inspector = inspect(connection)

        if "user_lesson_progress" not in inspector.get_table_names():
            return

        columns = {
            column["name"]
            for column in inspector.get_columns("user_lesson_progress")
        }

        if "practice_state" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE user_lesson_progress
                    ADD COLUMN practice_state JSON
                    NOT NULL DEFAULT '{}'
                    """
                )
            )
            connection.commit()

        connection.execute(
            text(
                """
                UPDATE user_lesson_progress
                SET practice_state = '{}'
                WHERE practice_state IS NULL
                """
            )
        )
        connection.commit()


ensure_lesson_practice_state()
