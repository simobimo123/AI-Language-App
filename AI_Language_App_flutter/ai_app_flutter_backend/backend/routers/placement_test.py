from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    LearningProfile,
    PlacementAttempt,
    PlacementAttemptWord,
    PlacementVocabulary,
    User,
)
from routers.auth import get_current_user
from schemas import (
    PlacementAttemptResponse,
    PlacementAttemptWordResponse,
    PlacementFinalizeResponse,
    PlacementWord,
    PlacementWordEvaluationResponse,
    PlacementWordsResponse,
)
from services.placement.config import PASS_THRESHOLD, WORDS_PER_LEVEL
from services.placement.leveling import (
    calculate_next_level,
    calculate_previous_level,
    normalize_language,
    normalize_level,
)
from services.placement.vocabulary import get_random_level_words
from services.placement.repository import get_attempt_or_404

router = APIRouter(prefix="/placement", tags=["Placement Test"])


class StartPlacementAttemptRequest(BaseModel):
    language: str = Field(min_length=2, max_length=10)


class StartPlacementAttemptResponse(BaseModel):
    attempt_id: int
    language: str
    status: str
    stage: str


@router.post("/attempts", response_model=StartPlacementAttemptResponse)
def start_placement_attempt(
    request: StartPlacementAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    language = normalize_language(request.language)

    active_attempts = db.query(PlacementAttempt).filter(
        PlacementAttempt.user_id == current_user.id,
        PlacementAttempt.language == language,
        PlacementAttempt.status == "active",
    ).all()

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


@router.get("/attempts/{attempt_id}", response_model=PlacementAttemptResponse)
def get_placement_attempt(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )


def _get_expected_vocabulary_level(attempt: PlacementAttempt) -> str:
    if attempt.stage != "vocabulary":
        raise HTTPException(
            status_code=400,
            detail="This placement attempt is not at the vocabulary stage.",
        )

    if attempt.preliminary_level is None:
        return "A1"

    next_level = calculate_next_level(attempt.preliminary_level)
    if next_level is None:
        raise HTTPException(
            status_code=400,
            detail="This placement attempt has already reached C2.",
        )

    return next_level


@router.get("/words/{language}/{level}", response_model=PlacementWordsResponse)
def get_placement_words(
    language: str,
    level: str,
    attempt_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    language = normalize_language(language)
    level = normalize_level(level)

    if attempt_id is not None:
        attempt = get_attempt_or_404(
            attempt_id=attempt_id,
            current_user=current_user,
            db=db,
        )

        if attempt.status != "active":
            raise HTTPException(
                status_code=400,
                detail="This placement attempt is no longer active.",
            )

        if attempt.language != language:
            raise HTTPException(
                status_code=400,
                detail="Attempt language does not match requested language.",
            )

        expected_level = _get_expected_vocabulary_level(attempt)
        if level != expected_level:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid vocabulary level for this placement attempt. "
                    f"Expected {expected_level}, received {level}."
                ),
            )

    words = get_random_level_words(
        language=language,
        level=level,
        db=db,
    )

    if len(words) != WORDS_PER_LEVEL:
        raise HTTPException(
            status_code=500,
            detail=f"The placement test must contain exactly {WORDS_PER_LEVEL} words.",
        )

    if attempt_id is not None:
        db.query(PlacementAttemptWord).filter(
            PlacementAttemptWord.attempt_id == attempt_id
        ).delete(synchronize_session=False)

        for position, word in enumerate(words, start=1):
            db.add(
                PlacementAttemptWord(
                    attempt_id=attempt_id,
                    placement_vocabulary_id=word.id,
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


class EvaluatePlacementWordsRequest(BaseModel):
    attempt_id: int = Field(ge=1)
    selected_word_ids: list[int] = Field(
        default_factory=list,
        max_length=WORDS_PER_LEVEL,
    )


@router.post(
    "/attempts/{attempt_id}/words/evaluate",
    response_model=PlacementWordEvaluationResponse,
)
def evaluate_placement_words_secure(
    attempt_id: int,
    request: EvaluatePlacementWordsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.attempt_id != attempt_id:
        raise HTTPException(status_code=400, detail="Attempt ID mismatch.")

    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.status != "active":
        raise HTTPException(
            status_code=400,
            detail="This placement attempt is no longer active.",
        )

    if attempt.stage != "vocabulary":
        raise HTTPException(
            status_code=400,
            detail="This placement attempt is not at the vocabulary stage.",
        )

    attempt_words = db.query(PlacementAttemptWord).filter(
        PlacementAttemptWord.attempt_id == attempt.id
    ).order_by(
        PlacementAttemptWord.position.asc()
    ).all()

    if len(attempt_words) != WORDS_PER_LEVEL:
        raise HTTPException(
            status_code=400,
            detail=f"This attempt must contain exactly {WORDS_PER_LEVEL} words.",
        )

    placement_word_ids = [
        item.placement_vocabulary_id for item in attempt_words
    ]

    selected_ids = list(dict.fromkeys(request.selected_word_ids))
    invalid_selected_ids = [
        word_id for word_id in selected_ids if word_id not in placement_word_ids
    ]

    if invalid_selected_ids:
        raise HTTPException(
            status_code=400,
            detail="One or more selected word IDs were not part of this attempt.",
        )

    selected_set = set(selected_ids)

    for item in attempt_words:
        item.was_selected = item.placement_vocabulary_id in selected_set

    placement_rows = db.query(PlacementVocabulary).filter(
        PlacementVocabulary.id.in_(placement_word_ids)
    ).all()

    if len(placement_rows) != WORDS_PER_LEVEL:
        raise HTTPException(
            status_code=500,
            detail="Placement vocabulary data is inconsistent.",
        )

    levels = {row.level for row in placement_rows}
    languages = {row.language for row in placement_rows}

    if len(levels) != 1 or len(languages) != 1:
        raise HTTPException(
            status_code=500,
            detail="Placement attempt contains mixed levels or languages.",
        )

    level = next(iter(levels))
    language = next(iter(languages))

    expected_level = _get_expected_vocabulary_level(attempt)
    if level != expected_level:
        raise HTTPException(
            status_code=500,
            detail=(
                "Placement attempt vocabulary level is inconsistent with "
                f"the expected level {expected_level}."
            ),
        )

    total_words = len(attempt_words)
    known_words = len(selected_set)
    percentage = known_words / total_words * 100.0
    passed = percentage >= PASS_THRESHOLD

    attempt.vocabulary_percentage = round(percentage, 2)

    # Vocabulary-only placement rule:
    #   >= 50% -> move up one level.
    #   < 50%  -> stay at the current level.
    # A1 failure stays A1. C2 success stays C2.
    if passed:
        final_or_next_level = calculate_next_level(level)

        attempt.preliminary_level = level

        if final_or_next_level is None:
            attempt.final_level = level
            attempt.stage = "finalized"
            attempt.status = "completed"
            next_level = None
        else:
            attempt.stage = "vocabulary"
            attempt.status = "active"
            next_level = final_or_next_level
    else:
        previous_level = calculate_previous_level(level)
        attempt.preliminary_level = previous_level
        attempt.final_level = previous_level
        attempt.stage = "finalized"
        attempt.status = "completed"
        next_level = None

    db.commit()

    return PlacementWordEvaluationResponse(
        language=language,
        level=level,
        total_words=total_words,
        known_words=known_words,
        percentage=round(percentage, 2),
        passed=passed,
        next_level=next_level,
        preliminary_level=attempt.preliminary_level,
    )


class FinalizePlacementAttemptRequest(BaseModel):
    attempt_id: int = Field(ge=1)


@router.post(
    "/attempts/{attempt_id}/finalize",
    response_model=PlacementFinalizeResponse,
)
def finalize_placement_attempt(
    attempt_id: int,
    request: FinalizePlacementAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.attempt_id != attempt_id:
        raise HTTPException(status_code=400, detail="Attempt ID mismatch.")

    attempt = get_attempt_or_404(
        attempt_id=attempt_id,
        current_user=current_user,
        db=db,
    )

    if attempt.final_level is None:
        raise HTTPException(
            status_code=400,
            detail="The placement test has not been completed yet.",
        )

    final_level = normalize_level(attempt.final_level)

    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == attempt.language,
    ).first()

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
        profile.progress = 0.0

    current_user.learning_language = attempt.language
    attempt.status = "completed"
    attempt.stage = "finalized"

    if attempt.completed_at is None:
        attempt.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    return PlacementFinalizeResponse(
        message="Placement finalized successfully",
        attempt_id=attempt.id,
        language=profile.language,
        level=profile.level,
        progress=profile.progress,
    )


@router.get(
    "/attempts/{attempt_id}/words",
    response_model=list[PlacementAttemptWordResponse],
)
def get_attempt_words(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = get_attempt_or_404(attempt_id, current_user, db)

    return db.query(PlacementAttemptWord).filter(
        PlacementAttemptWord.attempt_id == attempt.id
    ).order_by(
        PlacementAttemptWord.position.asc()
    ).all()
