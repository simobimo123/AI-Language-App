from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import PlacementQuizQuestion


# =========================================================
# English grammar / comprehension quiz bank.
#
# Each question: (question_text, choices, correct_index)
#
# 10 questions per level x 6 levels = 60 questions.
# =========================================================

ENGLISH_QUIZ = {
    "A1": [
        ("She ___ a teacher.",
         ["is", "are", "am", "be"], 0),
        ("I ___ from Morocco.",
         ["am", "is", "are", "be"], 0),
        ("They ___ students.",
         ["is", "am", "are", "be"], 2),
        ("This is ___ apple.",
         ["a", "an", "the", "some"], 1),
        ("We ___ happy today.",
         ["is", "am", "are", "be"], 2),
        ("He ___ like coffee.",
         ["don't", "doesn't", "isn't", "aren't"], 1),
        ("___ you like tea?",
         ["Do", "Does", "Is", "Are"], 0),
        ("There ___ a book on the table.",
         ["is", "are", "am", "be"], 0),
        ("My sister ___ two cats.",
         ["have", "has", "having", "had"], 1),
        ("___ is your name?",
         ["What", "Who", "Where", "When"], 0),
    ],

    "A2": [
        ("Yesterday, I ___ to the market.",
         ["go", "went", "gone", "going"], 1),
        ("She is taller ___ her brother.",
         ["than", "then", "that", "as"], 0),
        ("We ___ watching TV when he called.",
         ["was", "were", "is", "are"], 1),
        ("He has lived here ___ 2010.",
         ["for", "since", "from", "at"], 1),
        ("This book is ___ interesting than that one.",
         ["more", "most", "much", "many"], 0),
        ("I ___ finished my homework yet.",
         ["haven't", "didn't", "don't", "wasn't"], 0),
        ("They will arrive ___ Monday.",
         ["in", "on", "at", "by"], 1),
        ("She usually ___ up early.",
         ["get", "gets", "getting", "got"], 1),
        ("Can you tell me ___ the station is?",
         ["where", "what", "why", "who"], 0),
        ("He is good ___ playing football.",
         ["at", "in", "on", "for"], 0),
    ],

    "B1": [
        ("If it rains, we ___ stay home.",
         ["will", "would", "are", "were"], 0),
        ("I ___ never been to Japan.",
         ["have", "has", "had", "having"], 0),
        ("He suggested ___ a break.",
         ["take", "to take", "taking", "took"], 2),
        ("By the time we arrived, the movie ___ started.",
         ["already", "had already", "has already", "was already"], 1),
        ("She said she ___ tired.",
         ["is", "was", "be", "being"], 1),
        ("I wish I ___ more time.",
         ["have", "had", "has", "having"], 1),
        ("The book ___ by millions of people.",
         ["read", "reads", "has been read", "was reading"], 2),
        ("You ___ smoke here, it's not allowed.",
         ["mustn't", "don't have to", "shouldn't have to", "can"], 0),
        ("He apologized ___ being late.",
         ["for", "to", "about", "of"], 0),
        ("She ___ finish the report by tomorrow.",
         ["must", "has to", "should", "needs to"], 0),
    ],

    "B2": [
        ("She told me that she ___ the exam the day before.",
         ["passed", "had passed", "has passed", "was passing"], 1),
        ("Despite ___ hard, he failed the exam.",
         ["study", "to study", "studying", "studied"], 2),
        ("Had I known, I ___ come earlier.",
         ["would", "would have", "will", "will have"], 1),
        ("The bridge ___ next year.",
         ["will build", "will be built", "is building", "built"], 1),
        ("Not only ___ late, but he also forgot his notes.",
         ["he was", "was he", "he is", "is he"], 1),
        ("It's high time we ___ a decision.",
         ["make", "made", "making", "makes"], 1),
        ("She's the woman ___ car was stolen.",
         ["who", "whose", "which", "that"], 1),
        ("I'd rather you ___ that.",
         ["don't do", "didn't do", "won't do", "not do"], 1),
        ("Rarely ___ such a beautiful sunset.",
         ["we have seen", "have we seen", "we saw", "did we saw"], 1),
        ("He denied ___ the money.",
         ["to steal", "stealing", "steal", "stolen"], 1),
    ],

    "C1": [
        ("No sooner ___ the office than the phone rang.",
         ["he had left", "had he left", "he left", "did he leave"], 1),
        ("The report, ___ findings were controversial, sparked debate.",
         ["which", "whose", "that", "who"], 1),
        ("Were it not for your help, I ___ have failed.",
         ["would", "will", "might", "would already"], 0),
        ("She's used to ___ long hours.",
         ["work", "working", "worked", "be working"], 1),
        ("The committee's decision was met with ___ criticism.",
         ["wide", "widely", "width", "widen"], 0),
        ("Little ___ that his career would take off.",
         ["he knew", "did he know", "he did know", "knew he"], 1),
        ("The evidence ___ to be inconclusive.",
         ["proved", "proving", "was proved", "is proving"], 0),
        ("I'd sooner resign ___ compromise my principles.",
         ["than", "from", "that", "as"], 0),
        ("The plan was, ___ , a complete failure.",
         ["however", "in effect", "moreover", "likewise"], 1),
        ("He spoke as ___ he owned the place.",
         ["if", "though", "if or though (both work)", "when"], 2),
    ],

    "C2": [
        ("She's not so much lazy ___ overwhelmed.",
         ["as", "than", "but", "that"], 0),
        ("Seldom ___ such dedication in a newcomer.",
         ["one witnesses", "does one witness", "one does witness", "witnesses one"], 1),
        ("His argument, ___ compelling, lacked hard evidence.",
         ["while", "despite", "because", "so"], 0),
        ("Had the board acted sooner, the crisis ___ averted.",
         ["would be", "could have been", "will be", "was"], 1),
        ("The proposal met with an unequivocal ___ from the committee.",
         ["reject", "rejection", "rejecting", "rejects"], 1),
        ("He is, ___ , the most qualified candidate.",
         ["arguably", "argue", "argues", "arguable"], 0),
        ("Under no circumstances ___ this information be disclosed.",
         ["should", "we should", "must", "we must"], 0),
        ("The findings, far from ___ , raised more questions than they answered.",
         ["conclusive", "being conclusive", "conclude", "concluded"], 1),
        ("So subtle was the change that ___ noticed.",
         ["nobody", "anybody", "everybody hardly", "hardly anybody"], 0),
        ("It is only ___ that we appreciate what we had.",
         ["in hindsight", "hindsight", "with hindsight", "on hindsight"], 0),
    ],
}


# =========================================================
# Validation
# =========================================================

for level, questions in ENGLISH_QUIZ.items():

    if len(questions) != 10:
        raise RuntimeError(
            f"{level} must contain exactly 10 questions, "
            f"but contains {len(questions)}."
        )

    for question_text, choices, correct_index in questions:

        if len(choices) < 2:
            raise RuntimeError(
                f"Question has fewer than 2 choices: "
                f"{question_text}"
            )

        if not (0 <= correct_index < len(choices)):
            raise RuntimeError(
                f"correct_index out of range for: "
                f"{question_text}"
            )


# =========================================================
# Seed database
# =========================================================

def seed_english_quiz():

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Remove the old English quiz bank before
        # re-inserting, so re-running this script is safe.
        # -------------------------------------------------

        db.execute(
            delete(PlacementQuizQuestion).where(
                PlacementQuizQuestion.language == "en"
            )
        )

        db.commit()

        inserted = 0

        for level, questions in ENGLISH_QUIZ.items():

            for question_text, choices, correct_index in questions:

                statement = (
                    insert(PlacementQuizQuestion)
                    .values(
                        language="en",
                        level=level,
                        question=question_text,
                        choices=choices,
                        correct_index=correct_index,
                        is_active=True,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_placement_quiz_question"
                    )
                )

                result = db.execute(statement)

                if result.rowcount == 1:
                    inserted += 1

        db.commit()

        print()
        print("==============================================")
        print("English placement quiz seeded.")
        print("==============================================")

        for level in ENGLISH_QUIZ:
            print(
                f"{level}: "
                f"{len(ENGLISH_QUIZ[level])} questions"
            )

        print("----------------------------------------------")
        print(
            f"Total inserted: {inserted}"
        )
        print("Expected: 60")
        print("==============================================")
        print()

    except Exception:
        db.rollback()

        print(
            "Failed to seed English placement quiz."
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_english_quiz()