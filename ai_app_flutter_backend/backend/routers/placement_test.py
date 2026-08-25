from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    PlacementVocabulary,
    PlacementQuizQuestion,
    LearningProfile,
    User,
)
from routers.auth import get_current_user


router = APIRouter(
    prefix="/placement",
    tags=["Placement Test"],
)


# =========================================================
# Configuration
# =========================================================
#
# The placement screening starts at A1.
#
# PRE_A1 is the result when the user does not reach A1.
#
# PRE_A1 itself does NOT need a separate placement word
# screening or confirmation quiz.
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


# Confirmation quiz configuration.
#
# This test runs only for A1..C2.
# PRE_A1 does not need a confirmation quiz.

QUIZ_QUESTIONS_PER_TEST = 10

QUIZ_PASS_THRESHOLD = 50.0


PlacementLevel = Literal[
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
]


# =========================================================
# Word response model
# =========================================================

class PlacementWord(BaseModel):
    id: int
    word: str
    level: PlacementLevel


class PlacementWordsResponse(BaseModel):
    language: str
    level: PlacementLevel
    words: list[PlacementWord]


# =========================================================
# Evaluate one level
# =========================================================

class PlacementWordEvaluationRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    level: PlacementLevel

    # The exact 20 words that were displayed to the user.
    presented_word_ids: list[int] = Field(
        min_length=1,
        max_length=20,
    )

    # The subset of presented words that the user said
    # they know.
    selected_word_ids: list[int] = Field(
        default_factory=list,
    )


class PlacementWordEvaluationResponse(BaseModel):
    language: str
    level: PlacementLevel

    total_words: int
    known_words: int
    percentage: float

    passed: bool

    next_level: str | None

    # Can now be:
    # PRE_A1, A1, A2, B1, B2, C1, C2
    preliminary_level: str


# =========================================================
# Confirmation quiz models
# =========================================================

class PlacementQuizQuestionOut(BaseModel):
    id: int
    question: str
    choices: list[str]


class PlacementQuizResponse(BaseModel):
    language: str
    level: PlacementLevel
    questions: list[PlacementQuizQuestionOut]


class PlacementQuizAnswer(BaseModel):
    question_id: int

    selected_index: int = Field(
        ge=0,
    )


class PlacementQuizEvaluationRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    level: PlacementLevel

    answers: list[PlacementQuizAnswer] = Field(
        min_length=1,
        max_length=QUIZ_QUESTIONS_PER_TEST,
    )


class PlacementQuizEvaluationResponse(BaseModel):
    language: str
    level: PlacementLevel

    total_questions: int
    correct_answers: int
    percentage: float

    passed: bool

    # The level the user should actually be placed at,
    # after confirmation.
    #
    # Can now be PRE_A1 when A1 confirmation is failed.
    final_level: str


# =========================================================
# Finalize placement
# =========================================================

class PlacementFinalizeRequest(BaseModel):
    language: str = Field(
        min_length=2,
        max_length=10,
    )

    # Final level can be:
    #
    # PRE_A1
    # A1
    # A2
    # B1
    # B2
    # C1
    # C2
    level: str = Field(
        min_length=2,
        max_length=10,
    )


class PlacementFinalizeResponse(BaseModel):
    message: str
    language: str
    level: str
    progress: float


# =========================================================
# Get random words from PostgreSQL
# =========================================================

def get_random_level_words(
    language: str,
    level: PlacementLevel,
    db: Session,
) -> list[PlacementVocabulary]:

    statement = (
        select(PlacementVocabulary)
        .where(
            PlacementVocabulary.language == language,
            PlacementVocabulary.level == level,
            PlacementVocabulary.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            WORDS_PER_LEVEL
        )
    )

    words = db.execute(
        statement
    ).scalars().all()

    # -----------------------------------------------------
    # We require exactly 20 words for a level.
    #
    # If the bank has fewer than 20 active words, the test
    # must not start because the result would be unreliable.
    # -----------------------------------------------------

    if len(words) < WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active vocabulary for "
                f"{language}/{level}. "
                f"Required: {WORDS_PER_LEVEL}, "
                f"available: {len(words)}."
            ),
        )

    return words


# =========================================================
# Get random quiz questions from PostgreSQL
# =========================================================

def get_random_quiz_questions(
    language: str,
    level: PlacementLevel,
    db: Session,
) -> list[PlacementQuizQuestion]:

    statement = (
        select(PlacementQuizQuestion)
        .where(
            PlacementQuizQuestion.language == language,
            PlacementQuizQuestion.level == level,
            PlacementQuizQuestion.is_active.is_(True),
        )
        .order_by(
            func.random()
        )
        .limit(
            QUIZ_QUESTIONS_PER_TEST
        )
    )

    questions = db.execute(
        statement
    ).scalars().all()

    if len(questions) < QUIZ_QUESTIONS_PER_TEST:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Not enough active quiz questions for "
                f"{language}/{level}. "
                f"Required: {QUIZ_QUESTIONS_PER_TEST}, "
                f"available: {len(questions)}."
            ),
        )

    return questions


# =========================================================
# Get placement words
# =========================================================

@router.get(
    "/words/{language}/{level}",
    response_model=PlacementWordsResponse,
)
def get_placement_words(
    language: str,
    level: PlacementLevel,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = language.strip().lower()

    words = get_random_level_words(
        language=language,
        level=level,
        db=db,
    )

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
# Evaluate vocabulary screening
# =========================================================

@router.post(
    "/words/evaluate",
    response_model=PlacementWordEvaluationResponse,
)
def evaluate_placement_words(
    request: PlacementWordEvaluationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = request.language.strip().lower()

    # -----------------------------------------------------
    # Remove duplicate IDs while preserving order.
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # The UI should send exactly 20 words.
    # -----------------------------------------------------

    if len(presented_ids) != WORDS_PER_LEVEL:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Exactly {WORDS_PER_LEVEL} "
                "presented word IDs are required."
            ),
        )

    # -----------------------------------------------------
    # A selected word must also be one of the words shown
    # to the user.
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Load the exact words that were presented.
    # -----------------------------------------------------

    statement = (
        select(PlacementVocabulary)
        .where(
            PlacementVocabulary.id.in_(
                presented_ids
            ),
            PlacementVocabulary.language == language,
            PlacementVocabulary.level == request.level,
            PlacementVocabulary.is_active.is_(True),
        )
    )

    presented_words = db.execute(
        statement
    ).scalars().all()

    # -----------------------------------------------------
    # Make sure all 20 IDs belong to this exact test level.
    # -----------------------------------------------------

    actual_presented_ids = {
        word.id
        for word in presented_words
    }

    missing_ids = [
        word_id
        for word_id in presented_ids
        if word_id not in actual_presented_ids
    ]

    if missing_ids:

        raise HTTPException(
            status_code=400,
            detail=(
                "Some presented word IDs are invalid, "
                "inactive, or belong to another level."
            ),
        )

    # -----------------------------------------------------
    # Count known words.
    # -----------------------------------------------------

    selected_id_set = set(
        selected_ids
    )

    known_words = len(
        selected_id_set
    )

    total_words = len(
        presented_words
    )

    percentage = (
        known_words
        / total_words
        * 100
    )

    passed = (
        percentage >= PASS_THRESHOLD
    )

    current_index = LEVELS.index(
        request.level
    )

    # =====================================================
    # Passed current level
    # =====================================================

    if passed:

        if current_index < len(LEVELS) - 1:

            next_level = LEVELS[
                current_index + 1
            ]

        else:

            next_level = None

        preliminary_level = (
            request.level
        )

    # =====================================================
    # Failed current level
    # =====================================================

    else:

        next_level = None

        if current_index == 0:

            # The user did not reach A1.
            #
            # This is now a REAL PRE_A1 placement.
            preliminary_level = "PRE_A1"

        else:

            preliminary_level = LEVELS[
                current_index - 1
            ]

    return PlacementWordEvaluationResponse(
        language=language,
        level=request.level,
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
# Get confirmation quiz
# =========================================================
#
# The confirmation quiz runs only for A1..C2.
#
# PRE_A1 does NOT have a confirmation quiz because it is
# already the lowest possible level.
# =========================================================

@router.get(
    "/quiz/{language}/{level}",
    response_model=PlacementQuizResponse,
)
def get_placement_quiz(
    language: str,
    level: PlacementLevel,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = language.strip().lower()

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
            )
            for question in questions
        ],
    )


# =========================================================
# Evaluate confirmation quiz
# =========================================================

@router.post(
    "/quiz/evaluate",
    response_model=PlacementQuizEvaluationResponse,
)
def evaluate_placement_quiz(
    request: PlacementQuizEvaluationRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = request.language.strip().lower()

    # -----------------------------------------------------
    # Remove duplicate question IDs while keeping the last
    # answer given for each one.
    # -----------------------------------------------------

    answers_by_question_id: dict[int, int] = {
        answer.question_id: answer.selected_index
        for answer in request.answers
    }

    question_ids = list(
        answers_by_question_id.keys()
    )

    # -----------------------------------------------------
    # Load the exact questions being answered, and make
    # sure they really belong to this language/level.
    # -----------------------------------------------------

    statement = (
        select(PlacementQuizQuestion)
        .where(
            PlacementQuizQuestion.id.in_(
                question_ids
            ),
            PlacementQuizQuestion.language == language,
            PlacementQuizQuestion.level == request.level,
            PlacementQuizQuestion.is_active.is_(True),
        )
    )

    questions = db.execute(
        statement
    ).scalars().all()

    found_ids = {
        question.id
        for question in questions
    }

    missing_ids = [
        question_id
        for question_id in question_ids
        if question_id not in found_ids
    ]

    if missing_ids:

        raise HTTPException(
            status_code=400,
            detail=(
                "Some answered question IDs are invalid, "
                "inactive, or belong to another level."
            ),
        )

    # -----------------------------------------------------
    # Score the quiz.
    # -----------------------------------------------------

    correct_answers = 0

    for question in questions:

        selected_index = answers_by_question_id[
            question.id
        ]

        if selected_index == question.correct_index:
            correct_answers += 1

    total_questions = len(
        questions
    )

    percentage = (
        correct_answers
        / total_questions
        * 100
    )

    passed = (
        percentage >= QUIZ_PASS_THRESHOLD
    )

    current_index = LEVELS.index(
        request.level
    )

    # =====================================================
    # Confirmed at this level.
    # =====================================================

    if passed:

        final_level = request.level

    # =====================================================
    # Not confirmed.
    #
    # A1 -> PRE_A1
    # A2 -> A1
    # B1 -> A2
    # ...
    # =====================================================

    else:

        if current_index == 0:

            final_level = "PRE_A1"

        else:

            final_level = LEVELS[
                current_index - 1
            ]

    return PlacementQuizEvaluationResponse(
        language=language,
        level=request.level,
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
# Finalize placement
# =========================================================
#
# Saves the final result of the placement flow into the
# user's LearningProfile, creating it if it does not exist
# yet, or updating it if the user retakes the test.
#
# Valid final levels:
#
# PRE_A1, A1, A2, B1, B2, C1, C2
# =========================================================

@router.post(
    "/finalize",
    response_model=PlacementFinalizeResponse,
)
def finalize_placement(
    request: PlacementFinalizeRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):
    language = request.language.strip().lower()

    level = request.level.strip().upper()

    if level not in ALL_LEVELS:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid level '{level}'. "
                f"Must be one of: {', '.join(ALL_LEVELS)}."
            ),
        )

    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == language,
    ).first()

    if profile is None:

        profile = LearningProfile(
            user_id=current_user.id,
            language=language,
            level=level,
            progress=0.0,
        )

        db.add(profile)

    else:

        # The user retook the placement test: refresh the
        # level and restart progress for this language.
        profile.level = level
        profile.progress = 0.0

    # -----------------------------------------------------
    # Keep the user's current learning language in sync
    # with the language they just completed placement for.
    # -----------------------------------------------------

    current_user.learning_language = language

    db.commit()
    db.refresh(profile)

    return PlacementFinalizeResponse(
        message="Placement finalized successfully",
        language=profile.language,
        level=profile.level,
        progress=profile.progress,
    )