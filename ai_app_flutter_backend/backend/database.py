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


# Create tables
Base.metadata.create_all(engine)


# Apply small schema upgrades for existing development databases.
with engine.connect() as connection:

    inspector = inspect(connection)

    columns = inspector.get_columns("words")

    column_names = [column["name"] for column in columns]

    if "learned" not in column_names:

        connection.execute(
            text(
                """
                ALTER TABLE words
                ADD COLUMN learned BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )

        connection.commit()

        print("Added 'learned' column to words table.")

    user_columns = inspector.get_columns("users")
    user_column_names = [column["name"] for column in user_columns]

    if "native_language" not in user_column_names:
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN native_language VARCHAR(10) NOT NULL DEFAULT 'ar'
                """
            )
        )
        connection.commit()

    if "learning_language" not in user_column_names:
        connection.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN learning_language VARCHAR(10) NOT NULL DEFAULT 'en'
                """
            )
        )
        connection.commit()


print("Database connected successfully!")
