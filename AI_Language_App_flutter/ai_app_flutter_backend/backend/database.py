import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from models import Base


# =========================================================
# Environment
# =========================================================

load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL must be set in the .env file"
    )


# =========================================================
# Database engine
# =========================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
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
# Migration helpers
# =========================================================

def table_exists(
    connection,
    table_name: str,
) -> bool:

    inspector = inspect(
        connection
    )

    return table_name in (
        inspector.get_table_names()
    )


def get_column_names(
    connection,
    table_name: str,
) -> set[str]:

    if not table_exists(
        connection,
        table_name,
    ):
        return set()

    inspector = inspect(
        connection
    )

    return {
        column["name"]
        for column in inspector.get_columns(
            table_name
        )
    }


def column_exists(
    connection,
    table_name: str,
    column_name: str,
) -> bool:

    return (
        column_name
        in get_column_names(
            connection,
            table_name,
        )
    )


def add_column_if_missing(
    connection,
    table_name: str,
    column_name: str,
    sql_type: str,
    nullable: bool = True,
    default_sql: str | None = None,
) -> bool:

    if not table_exists(
        connection,
        table_name,
    ):
        return False

    if column_exists(
        connection,
        table_name,
        column_name,
    ):
        return False

    nullable_clause = (
        ""
        if nullable
        else " NOT NULL"
    )

    default_clause = (
        f" DEFAULT {default_sql}"
        if default_sql is not None
        else ""
    )

    statement = f"""
        ALTER TABLE {table_name}
        ADD COLUMN {column_name} {sql_type}
        {nullable_clause}
        {default_clause}
    """

    connection.execute(
        text(statement)
    )

    connection.commit()

    print(
        f"Added column "
        f"{table_name}.{column_name}."
    )

    return True


def add_foreign_key_if_missing(
    connection,
    table_name: str,
    column_name: str,
    referred_table: str,
    referred_column: str = "id",
    constraint_name: str | None = None,
    on_delete: str | None = None,
) -> bool:

    if not table_exists(
        connection,
        table_name,
    ):
        return False

    if not table_exists(
        connection,
        referred_table,
    ):
        return False

    inspector = inspect(
        connection
    )

    foreign_keys = inspector.get_foreign_keys(
        table_name
    )

    for foreign_key in foreign_keys:

        constrained_columns = (
            foreign_key.get(
                "constrained_columns",
                [],
            )
        )

        if (
            column_name
            in constrained_columns
            and foreign_key.get(
                "referred_table"
            ) == referred_table
            and (
                referred_column
                in foreign_key.get(
                    "referred_columns",
                    [],
                )
            )
        ):
            return False

    if constraint_name is None:

        constraint_name = (
            f"fk_{table_name}_{column_name}"
        )

    on_delete_clause = ""

    if on_delete:

        on_delete_clause = (
            f" ON DELETE {on_delete}"
        )

    connection.execute(
        text(
            f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT {constraint_name}
            FOREIGN KEY ({column_name})
            REFERENCES {referred_table}({referred_column})
            {on_delete_clause}
            """
        )
    )

    connection.commit()

    print(
        f"Added foreign key "
        f"{table_name}.{column_name} -> "
        f"{referred_table}.{referred_column}."
    )

    return True


def create_index_if_missing(
    connection,
    index_name: str,
    table_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:

    if not table_exists(
        connection,
        table_name,
    ):
        return

    column_names = get_column_names(
        connection,
        table_name,
    )

    if not all(
        column in column_names
        for column in columns
    ):
        return

    column_sql = ", ".join(
        columns
    )

    unique_sql = (
        "UNIQUE "
        if unique
        else ""
    )

    connection.execute(
        text(
            f"""
            CREATE {unique_sql}INDEX IF NOT EXISTS
            {index_name}
            ON {table_name} ({column_sql})
            """
        )
    )

    connection.commit()


def create_unique_partial_index_if_missing(
    connection,
    index_name: str,
    table_name: str,
    columns: list[str],
    where_clause: str,
) -> None:

    if not table_exists(
        connection,
        table_name,
    ):
        return

    column_names = get_column_names(
        connection,
        table_name,
    )

    if not all(
        column in column_names
        for column in columns
    ):
        return

    column_sql = ", ".join(
        columns
    )

    connection.execute(
        text(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS
            {index_name}
            ON {table_name} ({column_sql})
            WHERE {where_clause}
            """
        )
    )

    connection.commit()


def expand_level_column(
    connection,
    table_name: str,
    column_name: str,
) -> None:

    if not table_exists(
        connection,
        table_name,
    ):
        return

    inspector = inspect(
        connection
    )

    columns = inspector.get_columns(
        table_name
    )

    target_column = next(
        (
            column
            for column in columns
            if column["name"] == column_name
        ),
        None,
    )

    if target_column is None:
        return

    current_type = str(
        target_column["type"]
    ).upper()

    if "VARCHAR(2)" not in current_type:
        return

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
        f"Expanded "
        f"{table_name}.{column_name} "
        f"to VARCHAR(10)."
    )


def verify_required_columns(
    connection,
    requirements: dict[str, set[str]],
) -> None:

    for table_name, required_columns in (
        requirements.items()
    ):

        if not table_exists(
            connection,
            table_name,
        ):
            raise RuntimeError(
                f"Required table '{table_name}' "
                f"does not exist."
            )

        actual_columns = get_column_names(
            connection,
            table_name,
        )

        missing = (
            required_columns
            - actual_columns
        )

        if missing:
            raise RuntimeError(
                f"Table '{table_name}' is missing "
                f"columns: {sorted(missing)}"
            )


# =========================================================
# Create all declared tables
# =========================================================
#
# This creates missing tables.
#
# Existing tables are not deleted.
# Existing columns are not removed.
# Explicit migrations below handle old databases.
# =========================================================

Base.metadata.create_all(
    engine
)


# =========================================================
# Explicit schema migrations
# =========================================================

with engine.connect() as connection:

    # =====================================================
    # 1. USERS
    # =====================================================

    add_column_if_missing(
        connection=connection,
        table_name="users",
        column_name="native_language",
        sql_type="VARCHAR(10)",
        nullable=False,
        default_sql="'ar'",
    )

    add_column_if_missing(
        connection=connection,
        table_name="users",
        column_name="learning_language",
        sql_type="VARCHAR(10)",
        nullable=False,
        default_sql="'en'",
    )

    add_column_if_missing(
        connection=connection,
        table_name="users",
        column_name="google_id",
        sql_type="VARCHAR(255)",
        nullable=True,
    )

    connection.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            uq_users_google_id_partial
            ON users (google_id)
            WHERE google_id IS NOT NULL
            """
        )
    )

    connection.commit()

    print(
        "Users schema verified."
    )


    # =====================================================
    # 2. LEARNING PROFILES
    # =====================================================

    expand_level_column(
        connection,
        "learning_profiles",
        "level",
    )

    print(
        "Learning profiles schema verified."
    )


    # =====================================================
    # 3. WORDS
    # =====================================================

    if table_exists(
        connection,
        "words",
    ):

        add_column_if_missing(
            connection=connection,
            table_name="words",
            column_name="learned",
            sql_type="BOOLEAN",
            nullable=False,
            default_sql="FALSE",
        )

        add_column_if_missing(
            connection=connection,
            table_name="words",
            column_name="learning_profile_id",
            sql_type="INTEGER",
            nullable=True,
        )

        add_column_if_missing(
            connection=connection,
            table_name="words",
            column_name="vocabulary_entry_id",
            sql_type="INTEGER",
            nullable=True,
        )

        add_column_if_missing(
            connection=connection,
            table_name="words",
            column_name="vocabulary_form_id",
            sql_type="INTEGER",
            nullable=True,
        )

        word_columns = get_column_names(
            connection,
            "words",
        )

        # -------------------------------------------------
        # Old language-based migration
        # -------------------------------------------------

        if "language" in word_columns:

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
                "Migrated existing words "
                "using legacy language."
            )

        # -------------------------------------------------
        # Fallback to user's current learning language
        #
        # FIXED:
        # PostgreSQL does not allow referencing the target
        # UPDATE alias "w" from inside a JOIN ... ON clause
        # in this form.
        # -------------------------------------------------

        connection.execute(
            text(
                """
                UPDATE words AS w
                SET learning_profile_id = lp.id
                FROM learning_profiles AS lp,
                     users AS u
                WHERE lp.user_id = w.user_id
                  AND u.id = w.user_id
                  AND lp.language = u.learning_language
                  AND w.learning_profile_id IS NULL
                """
            )
        )

        connection.commit()

        remaining_words_without_profile = (
            connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM words
                    WHERE learning_profile_id IS NULL
                    """
                )
            ).scalar_one()
        )

        if (
            remaining_words_without_profile == 0
        ):

            connection.execute(
                text(
                    """
                    ALTER TABLE words
                    ALTER COLUMN learning_profile_id
                    SET NOT NULL
                    """
                )
            )

            connection.commit()

            print(
                "Made words.learning_profile_id required."
            )

        else:

            print(
                "WARNING: "
                f"{remaining_words_without_profile} "
                "word(s) still have no learning profile."
            )

            print(
                "Keeping words.learning_profile_id nullable "
                "until the remaining records are repaired."
            )

        # -------------------------------------------------
        # Foreign keys
        # -------------------------------------------------

        add_foreign_key_if_missing(
            connection=connection,
            table_name="words",
            column_name="learning_profile_id",
            referred_table="learning_profiles",
            constraint_name="fk_words_learning_profile",
            on_delete="CASCADE",
        )

        add_foreign_key_if_missing(
            connection=connection,
            table_name="words",
            column_name="vocabulary_entry_id",
            referred_table="vocabulary_entries",
            constraint_name="fk_words_vocabulary_entry",
            on_delete="SET NULL",
        )

        add_foreign_key_if_missing(
            connection=connection,
            table_name="words",
            column_name="vocabulary_form_id",
            referred_table="vocabulary_forms",
            constraint_name="fk_words_vocabulary_form",
            on_delete="SET NULL",
        )

        create_index_if_missing(
            connection,
            "ix_words_learning_profile_id",
            "words",
            ["learning_profile_id"],
        )

        create_index_if_missing(
            connection,
            "ix_words_vocabulary_entry_id",
            "words",
            ["vocabulary_entry_id"],
        )

        create_index_if_missing(
            connection,
            "ix_words_vocabulary_form_id",
            "words",
            ["vocabulary_form_id"],
        )

        # Do not delete the legacy language column yet.
        if (
            "language"
            in get_column_names(
                connection,
                "words",
            )
        ):

            print(
                "Legacy words.language retained "
                "for data safety."
            )

    print(
        "Words schema verified."
    )


    # =====================================================
    # 4. PRE-A1 / CEFR COLUMN WIDTH
    # =====================================================

    level_columns = [
        (
            "learning_profiles",
            "level",
        ),
        (
            "vocabulary_senses",
            "cefr_level",
        ),
        (
            "vocabulary_examples",
            "level",
        ),
        (
            "placement_vocabulary",
            "level",
        ),
        (
            "placement_quiz_questions",
            "level",
        ),
        (
            "course_lessons",
            "level",
        ),
        (
            "placement_attempts",
            "preliminary_level",
        ),
        (
            "placement_attempts",
            "final_level",
        ),
    ]

    for (
        table_name,
        column_name,
    ) in level_columns:

        expand_level_column(
            connection,
            table_name,
            column_name,
        )

    print(
        "PRE_A1 support verified."
    )


    # =====================================================
    # 5. VOCABULARY ENTRIES
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_entries",
        "normalized_lemma",
        "VARCHAR(255)",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_entries",
        "enrichment_status",
        "VARCHAR(30)",
        nullable=False,
        default_sql="'partial'",
    )

    add_column_if_missing(
        connection,
        "vocabulary_entries",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_entries",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_entries",
        "last_enriched_at",
        "TIMESTAMP",
        nullable=True,
    )

    # -----------------------------------------------------
    # Normalize old data.
    #
    # This intentionally does NOT use casefold() because
    # PostgreSQL lower() is safer as a database migration
    # primitive.
    # -----------------------------------------------------

    connection.execute(
        text(
            """
            UPDATE vocabulary_entries
            SET normalized_lemma = lower(trim(lemma))
            WHERE normalized_lemma IS NULL
            """
        )
    )

    connection.commit()

    create_index_if_missing(
        connection,
        "ix_vocabulary_entries_normalized_lemma",
        "vocabulary_entries",
        ["normalized_lemma"],
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_entry_language_normalized_lemma",
        "vocabulary_entries",
        [
            "language",
            "normalized_lemma",
        ],
    )

    print(
        "Vocabulary entry schema verified."
    )


    # =====================================================
    # 6. VOCABULARY RELATIONS
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_relations",
        "source_sense_id",
        "INTEGER",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_relations",
        "target_sense_id",
        "INTEGER",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_relations",
        "is_bidirectional",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_relations",
        "source",
        "VARCHAR(100)",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_relations",
        "source_version",
        "VARCHAR(100)",
        nullable=True,
    )

    add_foreign_key_if_missing(
        connection,
        "vocabulary_relations",
        "source_sense_id",
        "vocabulary_senses",
        constraint_name="fk_vocabulary_relation_source_sense",
        on_delete="CASCADE",
    )

    add_foreign_key_if_missing(
        connection,
        "vocabulary_relations",
        "target_sense_id",
        "vocabulary_senses",
        constraint_name="fk_vocabulary_relation_target_sense",
        on_delete="CASCADE",
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_relation_source_sense",
        "vocabulary_relations",
        ["source_sense_id"],
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_relation_target_sense",
        "vocabulary_relations",
        ["target_sense_id"],
    )

    print(
        "Vocabulary relations schema verified."
    )


    # =====================================================
    # 7. VOCABULARY FORMS
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_forms",
        "form_type",
        "VARCHAR(50)",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_forms",
        "is_lemma",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_forms_form_type",
        "vocabulary_forms",
        ["form_type"],
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_forms_is_lemma",
        "vocabulary_forms",
        ["is_lemma"],
    )

    print(
        "Vocabulary forms schema verified."
    )


    # =====================================================
    # 8. VOCABULARY SENSES
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_senses",
        "enrichment_status",
        "VARCHAR(30)",
        nullable=False,
        default_sql="'partial'",
    )

    add_column_if_missing(
        connection,
        "vocabulary_senses",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_senses",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_senses",
        "last_enriched_at",
        "TIMESTAMP",
        nullable=True,
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_sense_enrichment_status",
        "vocabulary_senses",
        ["enrichment_status"],
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_sense_entry_level",
        "vocabulary_senses",
        [
            "vocabulary_entry_id",
            "cefr_level",
        ],
    )

    print(
        "Vocabulary senses schema verified."
    )


    # =====================================================
    # 9. CEFR ASSESSMENTS
    # =====================================================

    if table_exists(
        connection,
        "vocabulary_cefr_assessments",
    ):

        add_column_if_missing(
            connection,
            "vocabulary_cefr_assessments",
            "is_selected",
            "BOOLEAN",
            nullable=False,
            default_sql="FALSE",
        )

        required_assessment_columns = {
            "vocabulary_sense_id",
            "cefr_level",
            "source",
            "source_version",
            "confidence",
            "is_selected",
        }

        assessment_columns = get_column_names(
            connection,
            "vocabulary_cefr_assessments",
        )

        missing_columns = (
            required_assessment_columns
            - assessment_columns
        )

        if missing_columns:

            raise RuntimeError(
                "Vocabulary CEFR assessment table is "
                "missing columns: "
                f"{sorted(missing_columns)}"
            )

        create_index_if_missing(
            connection,
            "ix_vocabulary_cefr_assessment_is_selected",
            "vocabulary_cefr_assessments",
            ["is_selected"],
        )

        create_index_if_missing(
            connection,
            "ix_vocabulary_cefr_assessment_sense_confidence",
            "vocabulary_cefr_assessments",
            [
                "vocabulary_sense_id",
                "confidence",
            ],
        )

    print(
        "Vocabulary CEFR assessment schema verified."
    )


    # =====================================================
    # 10. LOCALIZATIONS
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_sense_localizations",
        "enrichment_status",
        "VARCHAR(30)",
        nullable=False,
        default_sql="'partial'",
    )

    add_column_if_missing(
        connection,
        "vocabulary_sense_localizations",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_sense_localizations",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_sense_localizations",
        "last_enriched_at",
        "TIMESTAMP",
        nullable=True,
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_sense_localizations_generated_by_ai",
        "vocabulary_sense_localizations",
        ["generated_by_ai"],
    )

    print(
        "Vocabulary localizations schema verified."
    )


    # =====================================================
    # 11. TRANSLATIONS
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_translations",
        "translated_entry_id",
        "INTEGER",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_translations",
        "source_version",
        "VARCHAR(100)",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_translations",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_translations",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    add_foreign_key_if_missing(
        connection,
        "vocabulary_translations",
        "translated_entry_id",
        "vocabulary_entries",
        constraint_name="fk_vocabulary_translation_entry",
        on_delete="SET NULL",
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_translation_translated_entry",
        "vocabulary_translations",
        ["translated_entry_id"],
    )

    duplicate_primary_translations = (
        connection.execute(
            text(
                """
                SELECT
                    vocabulary_sense_id,
                    language,
                    COUNT(*) AS primary_count
                FROM vocabulary_translations
                WHERE is_primary = TRUE
                GROUP BY
                    vocabulary_sense_id,
                    language
                HAVING COUNT(*) > 1
                """
            )
        ).all()
    )

    if duplicate_primary_translations:

        print(
            "WARNING: duplicate primary vocabulary "
            "translations exist."
        )

        print(
            "Unique primary index will be skipped "
            "until the duplicates are repaired."
        )

    else:

        create_unique_partial_index_if_missing(
            connection,
            "uq_vocabulary_translation_primary",
            "vocabulary_translations",
            [
                "vocabulary_sense_id",
                "language",
            ],
            "is_primary = TRUE",
        )

    print(
        "Vocabulary translations schema verified."
    )


    # =====================================================
    # 12. EXAMPLES
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_examples",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_examples",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_example_sense_level",
        "vocabulary_examples",
        [
            "vocabulary_sense_id",
            "level",
        ],
    )

    print(
        "Vocabulary examples schema verified."
    )


    # =====================================================
    # 13. EXAMPLE TRANSLATIONS
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_example_translations",
        "source_version",
        "VARCHAR(100)",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "vocabulary_example_translations",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    add_column_if_missing(
        connection,
        "vocabulary_example_translations",
        "quality_score",
        "DOUBLE PRECISION",
        nullable=True,
    )

    duplicate_primary_example_translations = (
        connection.execute(
            text(
                """
                SELECT
                    vocabulary_example_id,
                    language,
                    COUNT(*) AS primary_count
                FROM vocabulary_example_translations
                WHERE is_primary = TRUE
                GROUP BY
                    vocabulary_example_id,
                    language
                HAVING COUNT(*) > 1
                """
            )
        ).all()
    )

    if duplicate_primary_example_translations:

        print(
            "WARNING: duplicate primary example "
            "translations exist."
        )

        print(
            "Unique primary example index will be skipped "
            "until the duplicates are repaired."
        )

    else:

        create_unique_partial_index_if_missing(
            connection,
            "uq_vocabulary_example_translation_primary",
            "vocabulary_example_translations",
            [
                "vocabulary_example_id",
                "language",
            ],
            "is_primary = TRUE",
        )

    print(
        "Vocabulary example translations schema verified."
    )


    # =====================================================
    # 14. MEDIA
    # =====================================================

    add_column_if_missing(
        connection,
        "vocabulary_media",
        "generated_by_ai",
        "BOOLEAN",
        nullable=False,
        default_sql="FALSE",
    )

    create_index_if_missing(
        connection,
        "ix_vocabulary_media_sense_type",
        "vocabulary_media",
        [
            "vocabulary_sense_id",
            "media_type",
        ],
    )

    print(
        "Vocabulary media schema verified."
    )


    # =====================================================
    # 15. PLACEMENT VOCABULARY
    # =====================================================

    add_column_if_missing(
        connection,
        "placement_vocabulary",
        "vocabulary_sense_id",
        "INTEGER",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "placement_vocabulary",
        "vocabulary_form_id",
        "INTEGER",
        nullable=True,
    )

    add_foreign_key_if_missing(
        connection,
        "placement_vocabulary",
        "vocabulary_sense_id",
        "vocabulary_senses",
        constraint_name="fk_placement_vocabulary_sense",
        on_delete="SET NULL",
    )

    add_foreign_key_if_missing(
        connection,
        "placement_vocabulary",
        "vocabulary_form_id",
        "vocabulary_forms",
        constraint_name="fk_placement_vocabulary_form",
        on_delete="SET NULL",
    )

    create_index_if_missing(
        connection,
        "ix_placement_vocabulary_sense_level",
        "placement_vocabulary",
        [
            "vocabulary_sense_id",
            "level",
        ],
    )

    print(
        "Placement vocabulary schema verified."
    )


    # =====================================================
    # 16. PLACEMENT QUIZ
    # =====================================================

    add_column_if_missing(
        connection,
        "placement_quiz_questions",
        "explanation",
        "TEXT",
        nullable=True,
    )

    add_column_if_missing(
        connection,
        "placement_quiz_questions",
        "question_type",
        "VARCHAR(30)",
        nullable=False,
        default_sql="'multiple_choice'",
    )

    print(
        "Placement quiz schema verified."
    )


    # =====================================================
    # 17. PLACEMENT ATTEMPTS
    # =====================================================

    required_placement_tables = {
        "placement_attempts",
        "placement_attempt_words",
        "placement_attempt_questions",
    }

    existing_tables = set(
        inspect(connection).get_table_names()
    )

    missing_placement_tables = (
        required_placement_tables
        - existing_tables
    )

    if missing_placement_tables:

        raise RuntimeError(
            "Missing placement tables: "
            f"{sorted(missing_placement_tables)}"
        )

    print(
        "Placement attempts schema verified."
    )


    # =====================================================
    # 18. COURSE LESSONS
    # =====================================================

    expand_level_column(
        connection,
        "course_lessons",
        "level",
    )

    print(
        "Course lessons schema verified."
    )


    # =====================================================
    # 19. USER LESSON PROGRESS
    # =====================================================

    if table_exists(
        connection,
        "user_lesson_progress",
    ):

        create_index_if_missing(
            connection,
            "ix_user_lesson_progress_user_lesson",
            "user_lesson_progress",
            [
                "user_id",
                "lesson_id",
            ],
        )

    print(
        "User lesson progress schema verified."
    )


    # =====================================================
    # 20. AI USAGE
    # =====================================================

    add_column_if_missing(
        connection,
        "ai_usage",
        "api_call_count",
        "INTEGER",
        nullable=False,
        default_sql="0",
    )

    add_column_if_missing(
        connection,
        "ai_usage",
        "prompt_tokens",
        "INTEGER",
        nullable=False,
        default_sql="0",
    )

    add_column_if_missing(
        connection,
        "ai_usage",
        "completion_tokens",
        "INTEGER",
        nullable=False,
        default_sql="0",
    )

    add_column_if_missing(
        connection,
        "ai_usage",
        "total_tokens",
        "INTEGER",
        nullable=False,
        default_sql="0",
    )

    add_column_if_missing(
        connection,
        "ai_usage",
        "estimated_cost",
        "DOUBLE PRECISION",
        nullable=False,
        default_sql="0",
    )

    print(
        "AI usage schema verified."
    )


    # =====================================================
    # 21. AI CONVERSATION
    # =====================================================

    add_column_if_missing(
        connection,
        "ai_conversation_messages",
        "conversation_id",
        "VARCHAR(100)",
        nullable=True,
    )

    create_index_if_missing(
        connection,
        "ix_ai_conversation_user_conversation_created",
        "ai_conversation_messages",
        [
            "user_id",
            "conversation_id",
            "created_at",
        ],
    )

    print(
        "AI conversation schema verified."
    )


    # =====================================================
    # 22. FINAL REQUIRED TABLE CHECK
    # =====================================================

    required_tables = {
        "users",
        "learning_profiles",
        "vocabulary_entries",
        "vocabulary_relations",
        "vocabulary_forms",
        "vocabulary_senses",
        "vocabulary_cefr_assessments",
        "vocabulary_sense_localizations",
        "vocabulary_translations",
        "vocabulary_examples",
        "vocabulary_example_translations",
        "vocabulary_media",
        "placement_vocabulary",
        "placement_quiz_questions",
        "placement_attempts",
        "placement_attempt_words",
        "placement_attempt_questions",
        "course_lessons",
        "user_lesson_progress",
        "words",
        "ai_usage",
        "ai_conversation_messages",
    }

    final_tables = set(
        inspect(connection).get_table_names()
    )

    missing_tables = (
        required_tables
        - final_tables
    )

    if missing_tables:

        raise RuntimeError(
            "Database schema verification failed. "
            "Missing tables: "
            f"{sorted(missing_tables)}"
        )


    # =====================================================
    # 23. FINAL REQUIRED COLUMN CHECK
    # =====================================================

    verify_required_columns(
        connection,
        {
            "vocabulary_entries": {
                "id",
                "language",
                "lemma",
                "normalized_lemma",
                "word",
                "part_of_speech",
                "pronunciation",
                "frequency_rank",
                "source",
                "source_version",
                "enrichment_status",
                "quality_score",
                "generated_by_ai",
                "last_enriched_at",
                "is_active",
            },
            "vocabulary_senses": {
                "id",
                "vocabulary_entry_id",
                "cefr_level",
                "enrichment_status",
                "quality_score",
                "generated_by_ai",
                "last_enriched_at",
                "is_active",
            },
            "vocabulary_relations": {
                "id",
                "source_entry_id",
                "target_entry_id",
                "source_sense_id",
                "target_sense_id",
                "relation_type",
                "language",
                "is_bidirectional",
                "source",
                "source_version",
            },
            "vocabulary_forms": {
                "id",
                "vocabulary_entry_id",
                "form",
                "normalized_form",
                "grammatical_features",
                "form_type",
                "is_lemma",
            },
            "vocabulary_translations": {
                "id",
                "vocabulary_sense_id",
                "language",
                "translation",
                "translated_entry_id",
                "is_primary",
                "source",
                "source_version",
                "generated_by_ai",
                "quality_score",
            },
            "vocabulary_sense_localizations": {
                "id",
                "vocabulary_sense_id",
                "language",
                "meaning",
                "definition",
                "enrichment_status",
                "quality_score",
                "generated_by_ai",
            },
            "vocabulary_examples": {
                "id",
                "vocabulary_sense_id",
                "sentence",
                "level",
                "generated_by_ai",
                "quality_score",
            },
            "vocabulary_example_translations": {
                "id",
                "vocabulary_example_id",
                "language",
                "translation",
                "is_primary",
                "source",
                "source_version",
                "generated_by_ai",
                "quality_score",
            },
            "vocabulary_media": {
                "id",
                "vocabulary_sense_id",
                "media_type",
                "url",
                "generated_by_ai",
            },
            "ai_usage": {
                "id",
                "user_id",
                "usage_date",
                "request_count",
                "api_call_count",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "estimated_cost",
            },
            "ai_conversation_messages": {
                "id",
                "user_id",
                "conversation_id",
                "role",
                "content",
                "created_at",
            },
        },
    )


    # =====================================================
    # 24. Final informational output
    # =====================================================

    print()
    print(
        "=================================================="
    )
    print(
        "DATABASE SCHEMA VERIFICATION COMPLETED"
    )
    print(
        "=================================================="
    )

    print(
        "Supported languages:"
    )

    print(
        ", ".join(
            [
                "ar",
                "de",
                "en",
                "es",
                "fa",
                "fr",
                "hi",
                "id",
                "it",
                "ja",
                "ko",
                "nl",
                "pl",
                "pt",
                "ru",
                "th",
                "tr",
                "uk",
                "vi",
                "zh",
            ]
        )
    )

    print()

    print(
        "Supported levels:"
    )

    print(
        "PRE_A1, A1, A2, B1, B2, C1, C2"
    )

    print()

    print(
        "Vocabulary architecture:"
    )

    print(
        "Entry -> Sense -> "
        "Localization / Translation / "
        "Example / Form / Relation / CEFR"
    )

    print()

    print(
        "Placement architecture:"
    )

    print(
        "PlacementAttempt -> "
        "Words / Questions -> Final level"
    )

    print()

    print(
        "AI architecture:"
    )

    print(
        "Database-first enrichment -> "
        "AI only for missing information"
    )

    print(
        "=================================================="
    )


# =========================================================
# Final message
# =========================================================

print(
    "Database connected successfully!"
)