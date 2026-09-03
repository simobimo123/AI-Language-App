from sqlalchemy import inspect, text

from database import engine



def ensure_learning_bank_item_type() -> None:
    """Add the item_type column to the existing personal words table.

    Existing rows are explicitly classified as words. New sentence rows use
    the same table with item_type="sentence".
    """
    with engine.connect() as connection:
        inspector = inspect(connection)

        if "words" not in inspector.get_table_names():
            return

        columns = {
            column["name"]
            for column in inspector.get_columns("words")
        }

        if "item_type" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE words
                    ADD COLUMN item_type VARCHAR(20)
                    NOT NULL DEFAULT 'word'
                    """
                )
            )
            connection.commit()

        connection.execute(
            text(
                """
                UPDATE words
                SET item_type = 'word'
                WHERE item_type IS NULL
                   OR item_type = ''
                """
            )
        )
        connection.commit()

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                ix_words_item_type
                ON words (item_type)
                """
            )
        )
        connection.commit()


ensure_learning_bank_item_type()
