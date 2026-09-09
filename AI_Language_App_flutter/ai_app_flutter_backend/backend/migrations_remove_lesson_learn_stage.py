from sqlalchemy import inspect, text

from database import engine


def remove_lesson_learn_stage() -> None:
    """Remove the obsolete first lesson stage and its deterministic exercise tables."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        if "user_lesson_stage_progress" in tables:
            # Existing users should start directly at AI teaching. Preserve
            # teaching/practice completion where it already exists.
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

            columns = {
                column["name"]
                for column in inspect(connection).get_columns("user_lesson_stage_progress")
            }
            for column in (
                "learn_status",
                "learn_started_at",
                "learn_completed_at",
            ):
                if column in columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE user_lesson_stage_progress DROP COLUMN IF EXISTS {column}"
                        )
                    )

        # These tables existed only for the removed deterministic learning stage.
        if "lesson_learning_questions" in tables:
            connection.execute(text("DROP TABLE IF EXISTS lesson_learning_questions"))
        if "lesson_learning_items" in tables:
            connection.execute(text("DROP TABLE IF EXISTS lesson_learning_items"))


remove_lesson_learn_stage()
