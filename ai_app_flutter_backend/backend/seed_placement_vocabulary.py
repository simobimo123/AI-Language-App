from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import PlacementVocabulary
from routers.placement_test import VOCABULARY_BANK


def seed_placement_vocabulary():
    db = SessionLocal()

    try:
        inserted_count = 0
        skipped_count = 0

        # -------------------------------------------------
        # Convert the existing vocabulary bank into rows.
        # -------------------------------------------------

        for language, levels in VOCABULARY_BANK.items():

            for level, words in levels.items():

                for word in words:

                    normalized_word = word.strip()

                    if not normalized_word:
                        continue

                    statement = (
                        insert(PlacementVocabulary)
                        .values(
                            language=language,
                            level=level,
                            word=normalized_word,
                            is_active=True,
                        )
                        .on_conflict_do_nothing(
                            constraint="uq_placement_vocabulary"
                        )
                    )

                    result = db.execute(
                        statement
                    )

                    if result.rowcount == 1:
                        inserted_count += 1
                    else:
                        skipped_count += 1

        db.commit()

        print()
        print("==============================================")
        print("Placement vocabulary seeding completed.")
        print("==============================================")
        print(
            f"Inserted: {inserted_count}"
        )
        print(
            f"Skipped existing: {skipped_count}"
        )
        print("==============================================")
        print()

    except Exception:
        db.rollback()

        print(
            "Placement vocabulary seeding failed."
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_placement_vocabulary()