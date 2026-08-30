from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from database import SessionLocal
from models import PlacementVocabulary


ENGLISH_VOCABULARY = {
    # =====================================================
    # PRE-A1
    # =====================================================
    #
    # Very basic vocabulary for complete beginners.
    #
    "PRE_A1": [
        "I", "you", "he", "she", "we",
        "they", "my", "your", "his", "her",
        "hello", "hi", "bye", "yes", "no",
        "please", "thanks", "sorry", "help", "okay",
        "name", "friend", "family", "mother", "father",
        "mom", "dad", "boy", "girl", "baby",
        "man", "woman", "child", "person", "people",
        "home", "house", "room", "door", "bed",
        "chair", "table", "book", "pen", "phone",
        "car", "bus", "school", "class", "teacher",
        "water", "milk", "bread", "apple", "food",
        "tea", "coffee", "dog", "cat", "animal",
        "one", "two", "three", "four", "five",
        "six", "seven", "eight", "nine", "ten",
        "red", "blue", "green", "yellow", "black",
        "white", "big", "small", "good", "bad",
        "hot", "cold", "happy", "sad", "here",
        "there", "today", "now", "come", "go",
        "eat", "drink", "sleep", "look", "see",
        "like", "want", "have", "make", "give",
    ],

    # =====================================================
    # A1
    # =====================================================

    "A1": [
        "hello", "house", "water", "book", "food",
        "mother", "father", "school", "friend", "family",
        "name", "day", "night", "good", "bad",
        "big", "small", "eat", "drink", "sleep",
        "man", "woman", "child", "boy", "girl",
        "home", "room", "door", "table", "chair",
        "car", "bus", "train", "street", "city",
        "country", "work", "play", "walk", "run",
        "sit", "stand", "go", "come", "make",
        "take", "give", "see", "look", "know",
        "want", "like", "love", "need", "have",
        "get", "put", "open", "close", "today",
        "tomorrow", "yesterday", "morning", "evening", "time",
        "now", "here", "there", "yes", "no",
        "please", "thanks", "sorry", "help", "money",
        "phone", "bag", "clothes", "shoe", "apple",
        "bread", "milk", "coffee", "tea", "dog",
        "cat", "person", "people", "brother", "sister",
        "parent", "son", "daughter", "teacher", "student",
        "class", "lesson", "language", "word", "sentence",
    ],

    # =====================================================
    # A2
    # =====================================================

    "A2": [
        "usually", "because", "between", "important", "weekend",
        "station", "different", "together", "sometimes", "always",
        "before", "after", "remember", "forget", "decide",
        "invite", "arrive", "leave", "healthy", "expensive",
        "cheap", "early", "late", "busy", "free",
        "weather", "travel", "holiday", "ticket", "hotel",
        "restaurant", "market", "shop", "buy", "sell",
        "pay", "cost", "price", "problem", "question",
        "answer", "story", "idea", "plan", "change",
        "happen", "start", "finish", "continue", "stop",
        "learn", "practice", "study", "understand", "explain",
        "choose", "hope", "try", "visit", "meet",
        "return", "stay", "become", "feel", "seem",
        "believe", "agree", "disagree", "perhaps", "maybe",
        "enough", "already", "still", "yet", "again",
        "often", "rarely", "never", "almost", "quickly",
        "slowly", "carefully", "easily", "difficult", "simple",
        "possible", "ready", "alone", "afraid", "tired",
        "hungry", "thirsty", "happy", "angry", "worried",
        "interested", "boring", "useful", "famous", "local",
    ],

    # =====================================================
    # B1
    # =====================================================

    "B1": [
        "experience", "decision", "improve", "behavior", "environment",
        "relationship", "opportunity", "although", "advantage", "disadvantage",
        "solution", "purpose", "prepare", "suggest", "describe",
        "develop", "protect", "reduce", "increase", "provide",
        "receive", "allow", "avoid", "compare", "contain",
        "depend", "discover", "imagine", "manage", "notice",
        "prefer", "realize", "recommend", "require", "support",
        "succeed", "achieve", "apply", "attend", "communicate",
        "consider", "create", "discuss", "encourage", "explain",
        "express", "forget", "forgive", "handle", "influence",
        "involve", "mention", "organize", "participate", "perform",
        "prevent", "produce", "promise", "recognize", "repair",
        "replace", "respond", "result", "share", "solve",
        "suppose", "survive", "train", "trust", "volunteer",
        "waste", "wonder", "accept", "afford", "advise",
        "announce", "belong", "borrow", "cancel", "cause",
        "collect", "connect", "contact", "control", "damage",
        "demand", "enter", "escape", "exist", "expect",
        "fail", "focus", "force", "guess", "include",
        "introduce", "join", "lend", "miss", "offer",
    ],

    # =====================================================
    # B2
    # =====================================================

    "B2": [
        "approach", "evidence", "require", "significant", "maintain",
        "consequence", "aware", "overall", "assume", "benefit",
        "challenge", "contribute", "determine", "establish", "factor",
        "impact", "indicate", "justify", "potential", "relevant",
        "acquire", "adapt", "adequate", "alternative", "analyze",
        "apparent", "appreciate", "arise", "assess", "authority",
        "capacity", "circumstance", "complex", "conduct", "consistent",
        "consume", "decline", "demonstrate", "derive", "distinguish",
        "efficient", "emerge", "enhance", "ensure", "equivalent",
        "evaluate", "expose", "feature", "flexible", "generate",
        "identify", "imply", "income", "instance", "interpret",
        "nevertheless", "objective", "obtain", "perceive", "policy",
        "principle", "propose", "pursue", "range", "react",
        "recover", "reliable", "restrict", "retain", "reveal",
        "seek", "shift", "specify", "stable", "strategy",
        "sufficient", "target", "transform", "trend", "valid",
        "vary", "whereas", "widespread", "accurate", "annual",
        "coherent", "crucial", "domestic", "economic", "ethical",
        "fundamental", "gradual", "independent", "initial", "logical",
        "mental", "negative", "obvious", "positive", "precise",
    ],

    # =====================================================
    # C1
    # =====================================================

    "C1": [
        "acknowledge", "controversial", "substantial", "contemporary", "underlying",
        "inevitable", "nevertheless", "distinguish", "implement", "perspective",
        "regulate", "sufficient", "transform", "framework", "interpret",
        "precise", "enhance", "demonstrate", "considerable", "comprehensive",
        "coordinate", "criteria", "decline", "manipulate", "reinforce",
        "facilitate", "constitute", "imply", "undergo", "advocate",
        "allocate", "ambiguous", "compatible", "compile", "constrain",
        "contradict", "desirable", "diminish", "discrete", "empirical",
        "hierarchy", "inherent", "integrate", "intervene", "invoke",
        "notion", "persistent", "preliminary", "sophisticated", "sustainable",
        "trigger", "valid", "voluntary", "widespread", "whereas",
        "likewise", "thereby", "hence", "conversely", "accordingly",
        "albeit", "nonetheless", "notwithstanding", "subjective", "objective",
        "rational", "coherent", "plausible", "explicit", "implicit",
        "intrinsic", "marginal", "rigorous", "arbitrary", "complementary",
        "unprecedented", "versatile", "cumulative", "detrimental", "feasible",
        "forthcoming", "meticulous", "pragmatic", "recurrent", "scrutiny",
        "subordinate", "consensus", "dilemma", "endeavor", "paradigm",
        "phenomenon", "hypothesis", "ideology", "incentive", "intervention",
        "trajectory", "vulnerability", "resilience", "counterpart", "constraint",
    ],

    # =====================================================
    # C2
    # =====================================================

    "C2": [
        "abate", "aberration", "abhor", "acclaimed", "acquiesce",
        "adamant", "alleviate", "amalgamate", "ambiguous", "ameliorate",
        "analogous", "anachronistic", "antagonistic", "appease", "arbitrary",
        "arduous", "articulate", "ascertain", "astute", "augment",
        "austere", "autonomous", "benevolent", "candid", "capricious",
        "clandestine", "coalesce", "cogent", "complacent", "conciliatory",
        "concomitant", "conundrum", "contentious", "contrive", "conventional",
        "corroborate", "cryptic", "cumulative", "cumbersome", "detrimental",
        "dichotomy", "discerning", "disseminate", "dubious", "eclectic",
        "eloquent", "empirical", "enigmatic", "exacerbate", "exasperate",
        "exemplary", "exhaustive", "expedient", "explicit", "extraneous",
        "formidable", "fortuitous", "fervent", "implicit", "incongruous",
        "inevitable", "ingenious", "inherent", "insidious", "intrepid",
        "juxtapose", "meticulous", "mitigate", "nuanced", "obsolete",
        "ostensibly", "paradigm", "paradoxical", "pervasive", "pragmatic",
        "precipitate", "preclude", "profound", "proliferate", "recalcitrant",
        "reconcile", "redundant", "scrutinize", "sporadic", "stringent",
        "subtle", "superfluous", "tentative", "ubiquitous", "unprecedented",
        "unequivocal", "versatile", "viable", "vindicate", "vehement",
        "vigilant", "volatile", "succinct", "salient", "unassailable",
    ],
}


# =========================================================
# Validation
# =========================================================

for level, words in ENGLISH_VOCABULARY.items():

    if len(words) != 100:
        raise RuntimeError(
            f"{level} must contain exactly 100 words, "
            f"but contains {len(words)}."
        )

    if len(set(words)) != 100:
        raise RuntimeError(
            f"{level} contains duplicate words."
        )


# =========================================================
# Seed database
# =========================================================

def seed_english_vocabulary():

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Remove the existing English placement vocabulary.
        # Other languages remain untouched.
        # -------------------------------------------------

        db.execute(
            delete(PlacementVocabulary).where(
                PlacementVocabulary.language == "en"
            )
        )

        db.commit()

        inserted = 0

        # -------------------------------------------------
        # Insert the English placement vocabulary.
        # -------------------------------------------------

        for level, words in ENGLISH_VOCABULARY.items():

            for word in words:

                statement = (
                    insert(PlacementVocabulary)
                    .values(
                        language="en",
                        level=level,
                        word=word,
                        is_active=True,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_placement_vocabulary"
                    )
                )

                result = db.execute(statement)

                if result.rowcount == 1:
                    inserted += 1

        db.commit()

        print()
        print("==============================================")
        print("English placement vocabulary seeded.")
        print("==============================================")

        for level in ENGLISH_VOCABULARY:
            print(
                f"{level}: "
                f"{len(ENGLISH_VOCABULARY[level])} words"
            )

        print("----------------------------------------------")
        print(
            f"Total inserted: {inserted}"
        )
        print("Expected: 700")
        print("==============================================")
        print()

    except Exception:
        db.rollback()

        print(
            "Failed to seed English placement vocabulary."
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_english_vocabulary()