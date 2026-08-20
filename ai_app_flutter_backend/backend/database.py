import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from models import Base


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(DATABASE_URL)


SessionLocal = sessionmaker(
    bind=engine
)


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================================================
# Create tables
# =========================================================

Base.metadata.create_all(engine)


# =========================================================
# Apply small schema upgrades
# for existing development databases
# =========================================================

with engine.connect() as connection:

    inspector = inspect(connection)

    # =====================================================
    # Users table
    # =====================================================

    user_columns = inspector.get_columns("users")

    user_column_names = [
        column["name"]
        for column in user_columns
    ]

    if "native_language" not in user_column_names:

        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN native_language VARCHAR(10)
                NOT NULL DEFAULT 'ar'
                """
            )
        )

        connection.commit()

        print(
            "Added 'native_language' column to users table."
        )

    if "learning_language" not in user_column_names:

        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN learning_language VARCHAR(10)
                NOT NULL DEFAULT 'en'
                """
            )
        )

        connection.commit()

        print(
            "Added 'learning_language' column to users table."
        )

    # =====================================================
    # Words table
    # =====================================================

    columns = inspector.get_columns("words")

    column_names = [
        column["name"]
        for column in columns
    ]

    # Add learned column if it does not exist
    if "learned" not in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD COLUMN learned BOOLEAN
                NOT NULL DEFAULT FALSE
                """
            )
        )

        connection.commit()

        print(
            "Added 'learned' column to words table."
        )

    # =====================================================
    # Add learning_profile_id
    # =====================================================

    if "learning_profile_id" not in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD COLUMN learning_profile_id INTEGER
                """
            )
        )

        connection.commit()

        print(
            "Added 'learning_profile_id' column to words table."
        )

        # -------------------------------------------------
        # Try to assign existing words using the old
        # language column when available.
        # -------------------------------------------------

        if "language" in column_names:

            connection.execute(
                text(
                    """
                    UPDATE words AS w
                    SET learning_profile_id = lp.id
                    FROM learning_profiles AS lp
                    WHERE lp.user_id = w.user_id
                      AND lp.language = w.language
                      AND w.learning_profile_id IS NULL
                    """
                )
            )

            connection.commit()

            print(
                "Assigned existing words using their old language."
            )

        # -------------------------------------------------
        # Fallback for old words that could not be matched.
        # -------------------------------------------------

        connection.execute(
            text(
                """
                UPDATE words AS w
                SET learning_profile_id = lp.id
                FROM learning_profiles AS lp
                JOIN users AS u
                    ON u.id = w.user_id
                WHERE lp.user_id = w.user_id
                  AND lp.language = u.learning_language
                  AND w.learning_profile_id IS NULL
                """
            )
        )

        connection.commit()

        print(
            "Applied fallback learning profiles to existing words."
        )

    # =====================================================
    # Make sure every word has a learning profile
    # =====================================================

    remaining = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM words
            WHERE learning_profile_id IS NULL
            """
        )
    ).scalar_one()

    if remaining > 0:

        print(
            f"Warning: {remaining} word(s) still have no "
            "learning profile."
        )

    else:

        # Make learning_profile_id required
        connection.execute(
            text(
                """
                ALTER TABLE words
                ALTER COLUMN learning_profile_id SET NOT NULL
                """
            )
        )

        connection.commit()

        print(
            "Made 'learning_profile_id' column required."
        )

    # =====================================================
    # Remove old language column
    # =====================================================

    inspector = inspect(connection)

    columns = inspector.get_columns("words")

    column_names = [
        column["name"]
        for column in columns
    ]

    if "language" in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                DROP COLUMN language
                """
            )
        )

        connection.commit()

        print(
            "Removed old 'language' column from words table."
        )

    # =====================================================
    # Add learning profile foreign key
    # =====================================================

    inspector = inspect(connection)

    foreign_keys = inspector.get_foreign_keys("words")

    has_learning_profile_fk = any(
        fk.get("referred_table") == "learning_profiles"
        and "learning_profile_id" in fk.get(
            "constrained_columns",
            []
        )
        for fk in foreign_keys
    )

    if not has_learning_profile_fk:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD CONSTRAINT fk_words_learning_profile
                FOREIGN KEY (learning_profile_id)
                REFERENCES learning_profiles(id)
                ON DELETE CASCADE
                """
            )
        )

        connection.commit()

        print(
            "Added learning_profile foreign key to words table."
        )


print("Database connected successfully!")