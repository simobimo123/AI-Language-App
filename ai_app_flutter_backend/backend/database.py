import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from models import Base


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL must be set in the .env file"
    )


# =========================================================
# Database engine
# =========================================================

engine = create_engine(
    DATABASE_URL
)


SessionLocal = sessionmaker(
    bind=engine
)


# =========================================================
# Database dependency
# =========================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================================================
# Create tables
# =========================================================
#
# This creates all tables defined in models.py that do not
# already exist.
#
# This now includes the new global vocabulary structure:
#
# - vocabulary_entries
# - vocabulary_senses
# - vocabulary_examples
# - vocabulary_media
#
# It also keeps the existing tables.
# =========================================================

Base.metadata.create_all(
    engine
)


# =========================================================
# Apply small schema upgrades
# for existing development databases
# =========================================================

with engine.connect() as connection:

    # =====================================================
    # Users table
    # =====================================================

    inspector = inspect(connection)

    user_columns = inspector.get_columns(
        "users"
    )

    user_column_names = [
        column["name"]
        for column in user_columns
    ]

    # =====================================================
    # native_language
    # =====================================================

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

    # =====================================================
    # learning_language
    # =====================================================

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
    # google_id
    # =====================================================

    if "google_id" not in user_column_names:

        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN google_id VARCHAR(255)
                """
            )
        )

        connection.commit()

        print(
            "Added 'google_id' column to users table."
        )

    # =====================================================
    # Unique Google ID index
    # =====================================================

    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            uq_users_google_id
            ON users (google_id)
            WHERE google_id IS NOT NULL
            """
        )
    )

    connection.commit()

    print(
        "Ensured unique Google ID index exists."
    )

    # =====================================================
    # Words table
    # =====================================================

    inspector = inspect(connection)

    columns = inspector.get_columns(
        "words"
    )

    column_names = [
        column["name"]
        for column in columns
    ]

    # =====================================================
    # learned
    # =====================================================

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
    # learning_profile_id
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
        # Old database:
        #
        # If the old words table had a language column,
        # try to match words with the corresponding
        # LearningProfile.
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
        # Fallback:
        #
        # Use the user's current learning language.
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
    # Check remaining words without profile
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

        # -------------------------------------------------
        # Only make the column required when every existing
        # row has a value.
        # -------------------------------------------------

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

    columns = inspector.get_columns(
        "words"
    )

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
    # Learning profile foreign key
    # =====================================================

    inspector = inspect(connection)

    foreign_keys = inspector.get_foreign_keys(
        "words"
    )

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


# =========================================================
# Final message
# =========================================================

print(
    "Database connected successfully!"
)