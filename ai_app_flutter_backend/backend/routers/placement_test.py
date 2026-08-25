from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db

from models import (
    PlacementVocabulary,
    PlacementQuizQuestion,
    PlacementAttempt,
    PlacementAttemptWord,
    PlacementAttemptQuestion,
    LearningProfile,
    User,
)

from schemas import (
    PlacementWord,
    PlacementWordsResponse,
    PlacementWordEvaluationResponse,
    PlacementQuizQuestionOut,
    PlacementQuizResponse,
    PlacementQuizEvaluationResponse,
    PlacementAttemptResponse,
    PlacementAttemptWordResponse,
    PlacementAttemptQuestionResponse,
    PlacementFinalizeResponse,
)

from routers.auth import get_current_user


router = APIRouter(
    prefix="/placement",
    tags=["Placement Test"],
)


# =========================================================
# Configuration
# =========================================================

LEVELS = [
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]

ALL_LEVELS = [
    "PRE_A1",
    *LEVELS,
]

PASS_THRESHOLD = 50.0

WORDS_PER_LEVEL = 20

QUIZ_QUESTIONS_PER_TEST = 10

QUIZ_PASS_THRESHOLD = 50.0


# =========================================================
# Helpers
# =========================================================

def normalize_language(
    language: str,
) -> str:
    return (
        language
        .strip()
        .lower()
    )


def normalize_level(
    level: str,
) -> str:
    normalized = (
        level
        .strip()
        .upper()
    )

    if normalized not in ALL_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid level '{normalized}'."
            ),
        )

    return normalized


def get_attempt_or_404(
    attempt_id: int,
    current_user: User,
    db: Session,
) -> PlacementAttempt:

    attempt = (
        db.query(PlacementAttempt)
        .filter(
            PlacementAttempt.id == attempt_id,
            PlacementAttempt.user_id
            == current_user.id,
        )
        .first()
    )

    if attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Placement attempt not found.",
        )

    return attempt


def get_random_level_words(
    language: str,
    level: str,
    db: Session,
) -> list[PlacementVocabulary]:

    statement = (
        select(
            PlacementVocabulary
        )
        .where(
            PlacementVocabulary.language
            == language,
            PlacementVocabulary.level
            == level,
            PlacementVocabulary.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            WORDS_PER_LEVEL
        )
    )

    words = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(words) < WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active vocabulary "
                f"for {language}/{level}. "
                f"Required: {WORDS_PER_LEVEL}, "
                f"available: {len(words)}."
            ),
        )

    return words


def get_random_quiz_questions(
    language: str,
    level: str,
    db: Session,
) -> list[PlacementQuizQuestion]:

    statement = (
        select(
            PlacementQuizQuestion
        )
        .where(
            PlacementQuizQuestion.language
            == language,
            PlacementQuizQuestion.level
            == level,
            PlacementQuizQuestion.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            QUIZ_QUESTIONS_PER_TEST
        )
    )

    questions = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(questions) < QUIZ_QUESTIONS_PER_TEST:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active quiz questions "
                f"for {language}/{level}. "
                f"Required: "
                f"{QUIZ_QUESTIONS_PER_TEST}, "
                f"available: {len(questions)}."
            ),
        )

    return questions


def get_current_learning_profile(
    language: str,
    current_user: User,
    db: Session,
) -> LearningProfile | None:

    return (
        db.query(
            LearningProfile
        )
        .filter(
            LearningProfile.user_id
            == current_user.id,
            LearningProfile.language
            == language,
        )
        .first()
    )


def calculate_previous_level(
    level: str,
) -> str:

    if level == "A1":
        return "PRE_A1"

    index = LEVELS.index(
        level
    )

    if index == 0:
        return "PRE_A1"

    return LEVELS[
        index - 1
    ]


def calculate_next_level(
    level: str,
) -> str | None:

    index = LEVELS.index(
        level
    )

    if index >= len(LEVELS) - 1:
        return None

    return LEVELS[
        index + 1
    ]


# =========================================================
# Start placement attempt
# =========================================================
#
# This is now the preferred flow.
#
# The client starts an attempt and receives an attempt ID.
# The server owns the state of that test.
# =========================================================

class StartPlacementAttemptRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )


class StartPlacementAttemptResponse(BaseModel):
    attempt_id: int
    language: str
    status: str
    stage: str


@router.post(
    "/attempts",
    response_model=StartPlacementAttemptResponse,
)
def start_placement_attempt(
    request: StartPlacementAttemptRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    language = normalize_language(
        request.language
    )

    # -----------------------------------------------------
    # If another active attempt exists for this user and
    # language, mark it abandoned before starting a new one.
    # -----------------------------------------------------

    active_attempts = (
        db.query(
            PlacementAttempt
        )
        .filter(
            PlacementAttempt.user_id
            == current_user.id,
            PlacementAttempt.language
            == language,
            PlacementAttempt.status
            == "active",
        )
        .all()
    )

    for old_attempt in active_attempts:
        old_attempt.status = "abandoned"

    attempt = PlacementAttempt(
        user_id=current_user.id,
        language=language,
        stage="vocabulary",
        status="active",
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return StartPlacementAttemptResponse(
        attempt_id=attempt.id,
        language=attempt.language,
        status=attempt.status,
        stage=attempt.stage,
    )


# =========================================================
# Get attempt
# =========================================================

@router.get(
    "/attempts/{attempt_id}",
    response_model=PlacementAttemptResponse,
)
def get_placement_attempt(
    attempt_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    return get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )


# =========================================================
# Get placement words - legacy compatible endpoint
# =========================================================

@router.get(
    "/words/{language}/{level}",
    response_model=PlacementWordsResponse,
)
def get_placement_words(
    language: str,
    level: str,
    attempt_id: int | None = Query(
        default=None,
        ge=1,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = normalize_language(
        language
    )

    level = normalize_level(
        level
    )

    if level == "PRE_A1":

        raise HTTPException(
            status_code=400,
            detail=(
                "PRE_A1 does not use vocabulary "
                "screening."
            ),
        )

    if attempt_id is not None:

        attempt = get_attempt_or_404(
            attempt_id=attempt_id,
            current_user=current_user,
            db=db,
        )

        if attempt.status != "active":
            raise HTTPException(
                status_code=400,
                detail=(
                    "This placement attempt "
                    "is no longer active."
                ),
            )

        if attempt.language != language:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Attempt language does not match "
                    "requested language."
                ),
            )

        if attempt.stage != "vocabulary":
            raise HTTPException(
                status_code=400,
                detail=(
                    "This attempt is not currently "
                    "at the vocabulary stage."
                ),
            )

    words = get_random_level_words(
        language=language,
        level=level,
        db=db,
    )

    # -----------------------------------------------------
    # Preferred secure flow:
    # persist the exact 20 words sent to the client.
    # -----------------------------------------------------

    if attempt_id is not None:

        # Remove any previous generated word list for
        # this active stage.
        (
            db.query(
                PlacementAttemptWord
            )
            .filter(
                PlacementAttemptWord.attempt_id
                == attempt_id
            )
            .delete(
                synchronize_session=False
            )
        )

        for position, word in enumerate(
            words,
            start=1,
        ):

            db.add(
                PlacementAttemptWord(
                    attempt_id=attempt_id,
                    placement_vocabulary_id=(
                        word.id
                    ),
                    position=position,
                    was_selected=False,
                )
            )

        db.commit()

    return PlacementWordsResponse(
        language=language,
        level=level,
        words=[
            PlacementWord(
                id=word.id,
                word=word.word,
                level=word.level,
            )
            for word in words
        ],
    )


# =========================================================
# Secure vocabulary evaluation models
# =========================================================

class EvaluatePlacementWordsRequest(BaseModel):
    attempt_id: int = Field(
        ge=1,
    )

    selected_word_ids: list[int] = Field(
        default_factory=list,
        max_length=20,
    )


# =========================================================
# Evaluate vocabulary screening - preferred secure flow
# =========================================================

@router.post(
    "/attempts/{attempt_id}/words/evaluate",
    response_model=PlacementWordEvaluationResponse,
)
def evaluate_placement_words_secure(
    attempt_id: int,
    request: EvaluatePlacementWordsRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    if request.attempt_id != attempt_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Attempt ID mismatch."
            ),
        )

    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.status != "active":

        raise HTTPException(
            status_code=400,
            detail=(
                "This placement attempt "
                "is no longer active."
            ),
        )

    if attempt.stage != "vocabulary":

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt is not at "
                "the vocabulary stage."
            ),
        )

    attempt_words = (
        db.query(
            PlacementAttemptWord
        )
        .filter(
            PlacementAttemptWord
            .attempt_id
            == attempt.id
        )
        .order_by(
            PlacementAttemptWord.position.asc()
        )
        .all()
    )

    if len(attempt_words) != WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt does not contain "
                f"exactly {WORDS_PER_LEVEL} "
                "placement words."
            ),
        )

    # -----------------------------------------------------
    # The level is determined by the selected attempt words.
    # The client never sends the level here.
    # -----------------------------------------------------

    placement_word_ids = [
        item.placement_vocabulary_id
        for item in attempt_words
    ]

    selected_ids = list(
        dict.fromkeys(
            request.selected_word_ids
        )
    )

    invalid_selected_ids = [
        word_id
        for word_id in selected_ids
        if word_id not in placement_word_ids
    ]

    if invalid_selected_ids:

        raise HTTPException(
            status_code=400,
            detail=(
                "One or more selected word IDs "
                "were not part of this placement attempt."
            ),
        )

    selected_set = set(
        selected_ids
    )

    for item in attempt_words:
        item.was_selected = (
            item.placement_vocabulary_id
            in selected_set
        )

    known_words = len(
        selected_set
    )

    total_words = len(
        attempt_words
    )

    percentage = (
        known_words
        / total_words
        * 100.0
    )

    # -----------------------------------------------------
    # Determine the actual level represented by this stage.
    #
    # We read the level from the placement rows in this
    # attempt instead of trusting the client.
    # -----------------------------------------------------

    placement_rows = (
        db.query(
            PlacementVocabulary
        )
        .filter(
            PlacementVocabulary.id.in_(
                placement_word_ids
            )
        )
        .all()
    )

    if len(placement_rows) != WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=500,
            detail=(
                "Placement vocabulary data is "
                "inconsistent."
            ),
        )

    levels = {
        row.level
        for row in placement_rows
    }

    languages = {
        row.language
        for row in placement_rows
    }

    if len(levels) != 1 or len(languages) != 1:

        raise HTTPException(
            status_code=500,
            detail=(
                "Placement attempt contains "
                "mixed levels or languages."
            ),
        )

    level = next(
        iter(levels)
    )

    language = next(
        iter(languages)
    )

    if level == "PRE_A1":

        raise HTTPException(
            status_code=500,
            detail=(
                "PRE_A1 cannot be used as "
                "a vocabulary screening level."
            ),
        )

    passed = (
        percentage >= PASS_THRESHOLD
    )

    if passed:

        preliminary_level = level

        next_level = (
            calculate_next_level(level)
        )

    else:

        preliminary_level = (
            calculate_previous_level(level)
        )

        next_level = None

    attempt.vocabulary_percentage = (
        round(
            percentage,
            2,
        )
    )

    attempt.preliminary_level = (
        preliminary_level
    )

    # -----------------------------------------------------
    # PRE_A1 finishes immediately.
    #
    # A1..C2 continue to confirmation quiz.
    # -----------------------------------------------------

    if preliminary_level == "PRE_A1":

        attempt.final_level = "PRE_A1"

        attempt.stage = "finalized"

        attempt.status = "completed"

    else:

        attempt.stage = "confirmation"

    db.commit()

    return PlacementWordEvaluationResponse(
        language=language,
        level=level,
        total_words=total_words,
        known_words=known_words,
        percentage=round(
            percentage,
            2,
        ),
        passed=passed,
        next_level=next_level,
        preliminary_level=preliminary_level,
    )


# =========================================================
# Legacy vocabulary evaluation
# =========================================================
#
# Kept temporarily so the current Flutter application does
# not break immediately.
#
# This endpoint is still validated strongly, but the secure
# attempt-based endpoint above is preferred.
# =========================================================

class LegacyPlacementWordEvaluationRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    level: str = Field(
        min_length=2,
        max_length=10,
    )

    presented_word_ids: list[int] = Field(
        min_length=20,
        max_length=20,
    )

    selected_word_ids: list[int] = Field(
        default_factory=list,
        max_length=20,
    )


@router.post(
    "/words/evaluate",
    response_model=PlacementWordEvaluationResponse,
)
def evaluate_placement_words_legacy(
    request: LegacyPlacementWordEvaluationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = normalize_language(
        request.language
    )

    level = normalize_level(
        request.level
    )

    if level == "PRE_A1":

        raise HTTPException(
            status_code=400,
            detail=(
                "PRE_A1 does not use "
                "vocabulary screening."
            ),
        )

    presented_ids = list(
        dict.fromkeys(
            request.presented_word_ids
        )
    )

    selected_ids = list(
        dict.fromkeys(
            request.selected_word_ids
        )
    )

    if len(presented_ids) != WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Exactly {WORDS_PER_LEVEL} "
                "presented word IDs are required."
            ),
        )

    presented_id_set = set(
        presented_ids
    )

    invalid_selected_ids = [
        word_id
        for word_id in selected_ids
        if word_id not in presented_id_set
    ]

    if invalid_selected_ids:

        raise HTTPException(
            status_code=400,
            detail=(
                "One or more selected word IDs "
                "were not part of the presented test."
            ),
        )

    statement = (
        select(
            PlacementVocabulary
        )
        .where(
            PlacementVocabulary.id.in_(
                presented_ids
            ),
            PlacementVocabulary.language
            == language,
            PlacementVocabulary.level
            == level,
            PlacementVocabulary.is_active.is_(True),
        )
    )

    presented_words = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(presented_words) != WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=400,
            detail=(
                "The presented word IDs do not form "
                "a valid 20-word test."
            ),
        )

    selected_set = set(
        selected_ids
    )

    known_words = len(
        selected_set
    )

    total_words = WORDS_PER_LEVEL

    percentage = (
        known_words
        / total_words
        * 100.0
    )

    passed = (
        percentage >= PASS_THRESHOLD
    )

    if passed:

        preliminary_level = level

        next_level = (
            calculate_next_level(level)
        )

    else:

        preliminary_level = (
            calculate_previous_level(level)
        )

        next_level = None

    return PlacementWordEvaluationResponse(
        language=language,
        level=level,
        total_words=total_words,
        known_words=known_words,
        percentage=round(
            percentage,
            2,
        ),
        passed=passed,
        next_level=next_level,
        preliminary_level=preliminary_level,
    )


# =========================================================
# Get confirmation quiz - preferred secure flow
# =========================================================

@router.get(
    "/attempts/{attempt_id}/quiz",
    response_model=PlacementQuizResponse,
)
def get_placement_quiz_secure(
    attempt_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.status != "active":

        raise HTTPException(
            status_code=400,
            detail=(
                "This placement attempt "
                "is no longer active."
            ),
        )

    if attempt.stage != "confirmation":

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt is not currently "
                "at the confirmation stage."
            ),
        )

    if attempt.preliminary_level not in LEVELS:

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt does not have "
                "a valid confirmation level."
            ),
        )

    level = attempt.preliminary_level

    questions = get_random_quiz_questions(
        language=attempt.language,
        level=level,
        db=db,
    )

    # -----------------------------------------------------
    # Persist exactly the questions shown to the user.
    # -----------------------------------------------------

    (
        db.query(
            PlacementAttemptQuestion
        )
        .filter(
            PlacementAttemptQuestion
            .attempt_id
            == attempt.id
        )
        .delete(
            synchronize_session=False
        )
    )

    for position, question in enumerate(
        questions,
        start=1,
    ):

        db.add(
            PlacementAttemptQuestion(
                attempt_id=attempt.id,
                placement_question_id=question.id,
                position=position,
            )
        )

    db.commit()

    return PlacementQuizResponse(
        language=attempt.language,
        level=level,
        questions=[
            PlacementQuizQuestionOut(
                id=question.id,
                question=question.question,
                choices=question.choices,
                question_type=(
                    question.question_type
                ),
                explanation=(
                    question.explanation
                ),
            )
            for question in questions
        ],
    )


# =========================================================
# Secure quiz evaluation
# =========================================================

class EvaluatePlacementQuizRequest(BaseModel):
    attempt_id: int = Field(
        ge=1,
    )

    answers: dict[int, int]


@router.post(
    "/attempts/{attempt_id}/quiz/evaluate",
    response_model=PlacementQuizEvaluationResponse,
)
def evaluate_placement_quiz_secure(
    attempt_id: int,
    request: EvaluatePlacementQuizRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    if request.attempt_id != attempt_id:

        raise HTTPException(
            status_code=400,
            detail="Attempt ID mismatch.",
        )

    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.status != "active":

        raise HTTPException(
            status_code=400,
            detail=(
                "This placement attempt "
                "is no longer active."
            ),
        )

    if attempt.stage != "confirmation":

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt is not at "
                "the confirmation stage."
            ),
        )

    attempt_questions = (
        db.query(
            PlacementAttemptQuestion
        )
        .filter(
            PlacementAttemptQuestion
            .attempt_id
            == attempt.id
        )
        .order_by(
            PlacementAttemptQuestion
            .position.asc()
        )
        .all()
    )

    if len(attempt_questions) != (
        QUIZ_QUESTIONS_PER_TEST
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "This attempt does not contain "
                f"exactly {QUIZ_QUESTIONS_PER_TEST} "
                "quiz questions."
            ),
        )

    # -----------------------------------------------------
    # Exactly 10 answers are required.
    # -----------------------------------------------------

    if len(request.answers) != (
        QUIZ_QUESTIONS_PER_TEST
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"Exactly "
                f"{QUIZ_QUESTIONS_PER_TEST} "
                "answers are required."
            ),
        )

    attempt_question_ids = {
        item.placement_question_id
        for item in attempt_questions
    }

    answer_question_ids = set(
        request.answers.keys()
    )

    if (
        answer_question_ids
        != attempt_question_ids
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Answers must correspond exactly "
                "to the questions assigned to "
                "this placement attempt."
            ),
        )

    question_rows = (
        db.query(
            PlacementQuizQuestion
        )
        .filter(
            PlacementQuizQuestion.id.in_(
                attempt_question_ids
            ),
            PlacementQuizQuestion.language
            == attempt.language,
            PlacementQuizQuestion.level
            == attempt.preliminary_level,
            PlacementQuizQuestion.is_active.is_(True),
        )
        .all()
    )

    question_by_id = {
        question.id: question
        for question in question_rows
    }

    if len(question_by_id) != (
        QUIZ_QUESTIONS_PER_TEST
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Placement quiz data is inconsistent."
            ),
        )

    correct_answers = 0

    for attempt_question in attempt_questions:

        question = question_by_id[
            attempt_question
            .placement_question_id
        ]

        selected_index = request.answers[
            question.id
        ]

        # Validate the selected choice against the
        # number of choices in the stored question.
        if (
            selected_index < 0
            or selected_index >= len(
                question.choices
            )
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid selected answer "
                    f"for question {question.id}."
                ),
            )

        attempt_question.selected_index = (
            selected_index
        )

        attempt_question.is_correct = (
            selected_index
            == question.correct_index
        )

        if attempt_question.is_correct:
            correct_answers += 1

    total_questions = (
        QUIZ_QUESTIONS_PER_TEST
    )

    percentage = (
        correct_answers
        / total_questions
        * 100.0
    )

    passed = (
        percentage
        >= QUIZ_PASS_THRESHOLD
    )

    level = attempt.preliminary_level

    if level not in LEVELS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid preliminary placement level."
            ),
        )

    if passed:

        final_level = level

    else:

        final_level = calculate_previous_level(
            level
        )

    attempt.confirmation_percentage = (
        round(
            percentage,
            2,
        )
    )

    attempt.final_level = final_level

    attempt.stage = "finalized"

    db.commit()

    return PlacementQuizEvaluationResponse(
        language=attempt.language,
        level=level,
        total_questions=total_questions,
        correct_answers=correct_answers,
        percentage=round(
            percentage,
            2,
        ),
        passed=passed,
        final_level=final_level,
    )


# =========================================================
# Legacy confirmation quiz endpoint
# =========================================================

@router.get(
    "/quiz/{language}/{level}",
    response_model=PlacementQuizResponse,
)
def get_placement_quiz_legacy(
    language: str,
    level: str,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = normalize_language(
        language
    )

    level = normalize_level(
        level
    )

    if level == "PRE_A1":

        raise HTTPException(
            status_code=400,
            detail=(
                "PRE_A1 does not use "
                "a confirmation quiz."
            ),
        )

    questions = get_random_quiz_questions(
        language=language,
        level=level,
        db=db,
    )

    return PlacementQuizResponse(
        language=language,
        level=level,
        questions=[
            PlacementQuizQuestionOut(
                id=question.id,
                question=question.question,
                choices=question.choices,
                question_type=(
                    question.question_type
                ),
                explanation=(
                    question.explanation
                ),
            )
            for question in questions
        ],
    )


# =========================================================
# Legacy confirmation quiz evaluation
# =========================================================
#
# Kept for compatibility.
#
# It still requires ALL 10 questions.
# The secure attempt-based route should be used by the new
# Flutter implementation.
# =========================================================

class LegacyPlacementQuizAnswer(BaseModel):
    question_id: int
    selected_index: int = Field(
        ge=0
    )


class LegacyPlacementQuizEvaluationRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    level: str = Field(
        min_length=2,
        max_length=10,
    )

    answers: list[
        LegacyPlacementQuizAnswer
    ] = Field(
        min_length=QUIZ_QUESTIONS_PER_TEST,
        max_length=QUIZ_QUESTIONS_PER_TEST,
    )


@router.post(
    "/quiz/evaluate",
    response_model=PlacementQuizEvaluationResponse,
)
def evaluate_placement_quiz_legacy(
    request: LegacyPlacementQuizEvaluationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = normalize_language(
        request.language
    )

    level = normalize_level(
        request.level
    )

    if level == "PRE_A1":

        raise HTTPException(
            status_code=400,
            detail=(
                "PRE_A1 does not use "
                "a confirmation quiz."
            ),
        )

    # -----------------------------------------------------
    # Reject duplicate question IDs.
    # -----------------------------------------------------

    if len({
        answer.question_id
        for answer in request.answers
    }) != QUIZ_QUESTIONS_PER_TEST:

        raise HTTPException(
            status_code=400,
            detail=(
                "Exactly 10 unique question IDs "
                "are required."
            ),
        )

    answers = {
        answer.question_id: answer.selected_index
        for answer in request.answers
    }

    question_ids = list(
        answers.keys()
    )

    statement = (
        select(
            PlacementQuizQuestion
        )
        .where(
            PlacementQuizQuestion.id.in_(
                question_ids
            ),
            PlacementQuizQuestion.language
            == language,
            PlacementQuizQuestion.level
            == level,
            PlacementQuizQuestion.is_active.is_(True),
        )
    )

    questions = (
        db.execute(
            statement
        )
        .scalars()
        .all()
    )

    if len(questions) != (
        QUIZ_QUESTIONS_PER_TEST
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "The answer set does not correspond "
                "to exactly 10 valid questions."
            ),
        )

    question_by_id = {
        question.id: question
        for question in questions
    }

    correct_answers = 0

    for question_id, selected_index in (
        answers.items()
    ):

        question = question_by_id[
            question_id
        ]

        if (
            selected_index < 0
            or selected_index >= len(
                question.choices
            )
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid selected answer "
                    f"for question {question_id}."
                ),
            )

        if (
            selected_index
            == question.correct_index
        ):
            correct_answers += 1

    total_questions = (
        QUIZ_QUESTIONS_PER_TEST
    )

    percentage = (
        correct_answers
        / total_questions
        * 100.0
    )

    passed = (
        percentage
        >= QUIZ_PASS_THRESHOLD
    )

    if passed:

        final_level = level

    else:

        final_level = calculate_previous_level(
            level
        )

    return PlacementQuizEvaluationResponse(
        language=language,
        level=level,
        total_questions=total_questions,
        correct_answers=correct_answers,
        percentage=round(
            percentage,
            2,
        ),
        passed=passed,
        final_level=final_level,
    )


# =========================================================
# Finalize placement from attempt
# =========================================================
#
# This is now the ONLY authoritative finalization route.
#
# The client sends only attempt_id.
#
# The server reads:
#
# attempt.final_level
#
# and does NOT trust a user-supplied level.
# =========================================================

class FinalizePlacementAttemptRequest(BaseModel):
    attempt_id: int = Field(
        ge=1
    )


@router.post(
    "/attempts/{attempt_id}/finalize",
    response_model=PlacementFinalizeResponse,
)
def finalize_placement_attempt(
    attempt_id: int,
    request: FinalizePlacementAttemptRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    if request.attempt_id != attempt_id:

        raise HTTPException(
            status_code=400,
            detail="Attempt ID mismatch.",
        )

    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.status == "completed":

        if attempt.final_level is None:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Completed placement attempt "
                    "has no final level."
                ),
            )

    elif attempt.status != "active":

        raise HTTPException(
            status_code=400,
            detail=(
                "This placement attempt "
                "cannot be finalized."
            ),
        )

    if attempt.final_level is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "The placement test has not "
                "been completed yet."
            ),
        )

    final_level = normalize_level(
        attempt.final_level
    )

    profile = (
        db.query(
            LearningProfile
        )
        .filter(
            LearningProfile.user_id
            == current_user.id,
            LearningProfile.language
            == attempt.language,
        )
        .first()
    )

    if profile is None:

        profile = LearningProfile(
            user_id=current_user.id,
            language=attempt.language,
            level=final_level,
            progress=0.0,
        )

        db.add(profile)

    else:

        profile.level = final_level

        # A new placement determines the starting point,
        # therefore course progress is reset.
        profile.progress = 0.0

    # Keep the current learning language in sync.
    current_user.learning_language = (
        attempt.language
    )

    attempt.status = "completed"
    attempt.stage = "finalized"

    if attempt.completed_at is None:
        from datetime import datetime

        attempt.completed_at = (
            datetime.utcnow()
        )

    db.commit()
    db.refresh(profile)

    return PlacementFinalizeResponse(
        message=(
            "Placement finalized successfully"
        ),
        attempt_id=attempt.id,
        language=profile.language,
        level=profile.level,
        progress=profile.progress,
    )


# =========================================================
# Legacy finalization
# =========================================================
#
# Disabled as an authoritative level setter.
#
# It is intentionally kept only as a compatibility endpoint
# that points the client toward the secure attempt-based flow.
# =========================================================

class LegacyFinalizePlacementRequest(BaseModel):
    attempt_id: int = Field(
        ge=1
    )


@router.post(
    "/finalize",
    response_model=PlacementFinalizeResponse,
)
def finalize_placement_legacy(
    request: LegacyFinalizePlacementRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    return finalize_placement_attempt(
        attempt_id=request.attempt_id,
        request=FinalizePlacementAttemptRequest(
            attempt_id=request.attempt_id
        ),
        current_user=current_user,
        db=db,
    )


# =========================================================
# Attempt words
# =========================================================

@router.get(
    "/attempts/{attempt_id}/words",
    response_model=list[PlacementAttemptWordResponse],
)
def get_attempt_words(
    attempt_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    attempt = get_attempt_or_404(
        attempt_id,
        current_user,
        db,
    )

    return (
        db.query(
            PlacementAttemptWord
        )
        .filter(
            PlacementAttemptWord.attempt_id
            == attempt.id
        )
        .order_by(
            PlacementAttemptWord.position.asc()
        )
        .all()
    )


# =========================================================
# Attempt questions
# =========================================================

@router.get(
    "/attempts/{attempt_id}/questions",
    response_model=list[PlacementAttemptQuestionResponse],
)
def get_attempt_questions(
    attempt_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    attempt = get_attempt_or_404(
        attempt_id,
        current_user,
        db,
    )

    return (
        db.query(
            PlacementAttemptQuestion
        )
        .filter(
            PlacementAttemptQuestion.attempt_id
            == attempt.id
        )
        .order_by(
            PlacementAttemptQuestion.position.asc()
        )
        .all()
    )