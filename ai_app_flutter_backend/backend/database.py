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

    if "vocabulary_entry_id" not in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD COLUMN vocabulary_entry_id INTEGER
                """
            )
        )

        connection.commit()

        print(
            "Added 'vocabulary_entry_id' column to words table."
        )

    if "vocabulary_form_id" not in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD COLUMN vocabulary_form_id INTEGER
                """
            )
        )

        connection.commit()

        print(
            "Added 'vocabulary_form_id' column to words table."
        )

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

    inspector = inspect(connection)

    foreign_keys = inspector.get_foreign_keys(
        "words"
    )

    has_vocabulary_entry_fk = any(
        fk.get("referred_table") == "vocabulary_entries"
        and "vocabulary_entry_id" in fk.get(
            "constrained_columns",
            []
        )
        for fk in foreign_keys
    )

    if not has_vocabulary_entry_fk:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD CONSTRAINT fk_words_vocabulary_entry
                FOREIGN KEY (vocabulary_entry_id)
                REFERENCES vocabulary_entries(id)
                ON DELETE SET NULL
                """
            )
        )

        connection.commit()

        print(
            "Added vocabulary entry foreign key to words table."
        )

    inspector = inspect(connection)

    foreign_keys = inspector.get_foreign_keys(
        "words"
    )

    has_vocabulary_form_fk = any(
        fk.get("referred_table") == "vocabulary_forms"
        and "vocabulary_form_id" in fk.get(
            "constrained_columns",
            []
        )
        for fk in foreign_keys
    )

    if not has_vocabulary_form_fk:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD CONSTRAINT fk_words_vocabulary_form
                FOREIGN KEY (vocabulary_form_id)
                REFERENCES vocabulary_forms(id)
                ON DELETE SET NULL
                """
            )
        )

        connection.commit()

        print(
            "Added vocabulary form foreign key to words table."
        )

    connection.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS
            ix_words_vocabulary_entry_id
            ON words (vocabulary_entry_id)
            """
        )
    )

    connection.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS
            ix_words_vocabulary_form_id
            ON words (vocabulary_form_id)
            """
        )
    )

    connection.commit()

    print(
        "Ensured vocabulary relationship indexes exist."
    )

    # =====================================================
    # PRE-A1 level column upgrade
    # =====================================================

    level_columns = [
        ("learning_profiles", "level"),
        ("vocabulary_senses", "cefr_level"),
        ("vocabulary_examples", "level"),
        ("placement_vocabulary", "level"),
        ("placement_quiz_questions", "level"),
        ("course_lessons", "level"),
    ]

    for table_name, column_name in level_columns:

        inspector = inspect(connection)

        table_columns = inspector.get_columns(
            table_name
        )

        target_column = next(
            (
                column
                for column in table_columns
                if column["name"] == column_name
            ),
            None,
        )

        if target_column is None:
            continue

        current_type = str(
            target_column["type"]
        ).upper()

        if "VARCHAR(2)" in current_type:

            connection.execute(
                text(
                    f"""
                    ALTER TABLE {table_name}
                    ALTER COLUMN {column_name}
                    TYPE VARCHAR(10)
                    USING {column_name}::VARCHAR(10)
                    """
                )
            )

            connection.commit()

            print(
                f"Expanded {table_name}.{column_name} "
                "to VARCHAR(10) for PRE_A1 support."
            )

    # =====================================================
    # Vocabulary CEFR assessments
    # =====================================================
    #
    # Base.metadata.create_all() creates this table for
    # existing databases without affecting existing data.
    #
    # The following check makes the upgrade visible and
    # verifies that the table exists.
    # =====================================================

    inspector = inspect(connection)

    table_names = inspector.get_table_names()

    if "vocabulary_cefr_assessments" in table_names:

        assessment_columns = inspector.get_columns(
            "vocabulary_cefr_assessments"
        )

        assessment_column_names = [
            column["name"]
            for column in assessment_columns
        ]

        required_assessment_columns = {
            "vocabulary_sense_id",
            "cefr_level",
            "source",
            "source_version",
            "confidence",
        }

        missing_assessment_columns = (
            required_assessment_columns
            - set(assessment_column_names)
        )

        if missing_assessment_columns:

            raise RuntimeError(
                "Vocabulary CEFR assessment table is missing "
                f"columns: {sorted(missing_assessment_columns)}"
            )

        print(
            "Vocabulary CEFR assessment table is ready."
        )

    else:

        raise RuntimeError(
            "Vocabulary CEFR assessment table was not created."
        )

    # =====================================================
    # Verify level columns
    # =====================================================

    print()
    print(
        "Level column upgrade check completed."
    )

    print(
        "Supported levels:"
    )

    print(
        "PRE_A1, A1, A2, B1, B2, C1, C2"
    )


# =========================================================
# Final message
# =========================================================

print(
    "Database connected successfully!"
)