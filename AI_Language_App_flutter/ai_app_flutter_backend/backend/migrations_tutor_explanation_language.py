from sqlalchemy import inspect, text

from database import engine


COLUMN_NAME = "tutor_explanation_language_mode"
DEFAULT_MODE = "native"


with engine.connect() as connection:
    inspector = inspect(connection)
    tables = inspector.get_table_names()

    if "users" in tables:
        columns = {
            column["name"]
            for column in inspector.get_columns("users")
        }

        if COLUMN_NAME not in columns:
            connection.execute(
                text(
                    f"""
                    ALTER TABLE users
                    ADD COLUMN {COLUMN_NAME} VARCHAR(20)
                    NOT NULL DEFAULT '{DEFAULT_MODE}'
                    """
                )
            )
            connection.commit()
            print(
                "Added users.tutor_explanation_language_mode."
            )
