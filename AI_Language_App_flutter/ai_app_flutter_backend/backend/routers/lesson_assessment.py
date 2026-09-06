import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import (
    CourseLesson,
    LearningProfile,
    User,
    UserLessonProgress,
)
from routers.auth import get_current_user
from routers.learning_path import (
    calculate_normal_progress,
    get_current_lesson,
    get_next_level,
    get_progress_map,
    get_or_create_lesson_progress,
    sync_learning_content,
)
from routers.lesson_ai import (
    _lesson_targets,
    _load_lesson_curriculum,
)
from schemas import (
    LessonAssessmentQuestion,
    LessonAssessmentResponse,
    LessonAssessmentResult,
    LessonAssessmentSubmitRequest,
)
from services.ai.normalization import normalize_language


router = APIRouter(
    prefix="/learning",
    tags=["Lesson Assessment"],
)

LESSONS_ROOT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "lessons"
)


# ============================================================================
# PROFILE / LESSON
# ============================================================================


def _get_current_profile(
    current_user: User,
    db: Session,
) -> LearningProfile:
    language = normalize_language(
        current_user.learning_language
    )

    profile = (
        db.query(LearningProfile)
        .filter(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == language,
        )
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current learning profile not found.",
        )

    return profile


def _get_lesson(
    lesson_id: int,
    current_user: User,
    db: Session,
) -> tuple[
    CourseLesson,
    LearningProfile,
    list[CourseLesson],
]:
    profile = _get_current_profile(
        current_user,
        db,
    )

    try:
        lessons = sync_learning_content(
            language=profile.language,
            level=profile.level,
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    lesson = next(
        (
            item
            for item in lessons
            if item.id == lesson_id
        ),
        None,
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found in the current curriculum.",
        )

    current_lesson = get_current_lesson(
        lessons=lessons,
        progress_map=get_progress_map(
            current_user.id,
            profile.id,
            [item.id for item in lessons],
            db,
        ),
    )

    if (
        current_lesson is None
        or current_lesson.id != lesson.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is currently locked.",
        )

    return lesson, profile, lessons


# ============================================================================
# ASSESSMENT LOADING
# ============================================================================


def _load_assessment(
    lesson: CourseLesson,
) -> dict:
    path = (
        LESSONS_ROOT
        / normalize_language(lesson.language)
        / str(lesson.level).upper()
        / f"lesson_{lesson.lesson_order:02d}.json"
    )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson assessment source file was not found.",
        ) from exc

    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson assessment source is invalid.",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lesson assessment source must be an object.",
        )

    source = data.get("end_test")

    if not isinstance(source, dict):
        source = data.get("assessment")

    if not isinstance(source, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This lesson has no final assessment.",
        )

    questions = source.get("questions")

    if not isinstance(questions, list) or not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This lesson has no assessment questions.",
        )

    key_sentences = data.get(
        "key_sentences",
        [],
    )

    if not isinstance(key_sentences, list):
        key_sentences = []

    try:
        passing_score = float(
            source.get(
                "passing_score",
                lesson.passing_score,
            )
        )
    except (TypeError, ValueError):
        passing_score = float(
            lesson.passing_score
        )

    return {
        "passing_score": passing_score,
        "questions": [
            item
            for item in questions
            if isinstance(item, dict)
        ],
        "key_sentences": [
            item
            for item in key_sentences
            if isinstance(item, dict)
        ],
    }


# ============================================================================
# LANGUAGE
# ============================================================================


def _instruction_language(
    current_user: User,
) -> str:
    return normalize_language(
        current_user.native_language
    )


# ============================================================================
# CONVERSATION / PRACTICE VALIDATION
# ============================================================================


def _resolve_conversation(
    current_user: User,
    conversation_id: str | None,
    lesson_id: int,
    profile: LearningProfile,
    curriculum: dict,
    db: Session,
) -> str:
    if (
        not conversation_id
        or not conversation_id.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Complete the translation check "
                "before starting the assessment."
            ),
        )

    candidate = conversation_id.strip()

    progress = db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id
            == current_user.id,
            UserLessonProgress.lesson_id
            == lesson_id,
        )
    ).scalar_one_or_none()

    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Complete the lesson practice "
                "and translation check before "
                "starting the assessment."
            ),
        )

    state = (
        progress.practice_state
        if isinstance(
            progress.practice_state,
            dict,
        )
        else {}
    )

    stored_conversation_id = str(
        state.get(
            "conversation_id",
            "",
        )
    ).strip()

    if (
        not stored_conversation_id
        or stored_conversation_id != candidate
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This lesson conversation "
                "is no longer active."
            ),
        )

    # ------------------------------------------------------------------------
    # TARGET PROGRESS
    # ------------------------------------------------------------------------

    targets = _lesson_targets(
        curriculum
    )

    required_target_ids = {
        str(target.get("id", "")).strip()
        for target in targets
        if target.get("required", True)
        and str(target.get("id", "")).strip()
    }

    practiced_raw = state.get(
        "practiced_target_ids",
        [],
    )

    # Backwards compatibility with older progress records.
    if not isinstance(practiced_raw, list):
        practiced_raw = state.get(
            "practiced_sentence_ids",
            [],
        )

    practiced_ids = {
        str(value).strip()
        for value in practiced_raw
        if str(value).strip()
    } if isinstance(
        practiced_raw,
        list,
    ) else set()

    if (
        not required_target_ids
        or not required_target_ids.issubset(
            practiced_ids
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Complete all target "
                "sentences before the assessment."
            ),
        )

    # ------------------------------------------------------------------------
    # TRANSLATION CHECK
    # ------------------------------------------------------------------------

    if state.get(
        "translation_check_passed"
    ) is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Pass the translation check "
                "before starting the assessment."
            ),
        )

    return candidate


# ============================================================================
# TRANSLATIONS
# ============================================================================


def _translation(
    question: dict,
    language: str,
) -> dict:
    translations = question.get(
        "translations"
    )

    if not isinstance(
        translations,
        dict,
    ):
        return {}

    value = translations.get(
        language
    )

    if isinstance(value, dict):
        return value

    value = translations.get("ar")

    return (
        value
        if isinstance(value, dict)
        else {}
    )


# ============================================================================
# PUBLIC QUESTIONS
# ============================================================================


def _public_questions(
    assessment: dict,
    instruction_language: str,
) -> list[LessonAssessmentQuestion]:
    result: list[
        LessonAssessmentQuestion
    ] = []

    for index, question in enumerate(
        assessment["questions"],
        start=1,
    ):
        question_id = str(
            question.get(
                "id",
                "",
            )
        ).strip()

        if not question_id:
            continue

        translation = _translation(
            question,
            instruction_language,
        )

        question_text = str(
            translation.get(
                "question",
                question.get(
                    "question",
                    "",
                ),
            )
        ).strip()

        raw_options = translation.get(
            "options",
            question.get(
                "options",
                [],
            ),
        )

        public_options: list[
            dict
        ] = []

        if isinstance(
            raw_options,
            list,
        ):
            for option_index, option in enumerate(
                raw_options,
                start=1,
            ):
                if isinstance(
                    option,
                    dict,
                ):
                    option_id = str(
                        option.get(
                            "id",
                            "",
                        )
                    ).strip()

                    text = str(
                        option.get(
                            "text",
                            "",
                        )
                    ).strip()

                else:
                    option_id = str(
                        option_index
                    )
                    text = str(
                        option
                    ).strip()

                if option_id and text:
                    public_options.append(
                        {
                            "id": option_id,
                            "text": text,
                        }
                    )

        try:
            order = int(
                question.get(
                    "order",
                    index,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            order = index

        result.append(
            LessonAssessmentQuestion(
                id=question_id,
                order=order,
                type=str(
                    question.get(
                        "type",
                        "multiple_choice",
                    )
                ),
                question=question_text,
                options=public_options,
            )
        )

    result.sort(
        key=lambda item: item.order
    )

    return result


# ============================================================================
# PUBLIC KEY SENTENCES
# ============================================================================


def _public_key_sentences(
    assessment: dict,
) -> list[dict]:
    result: list[dict] = []

    for item in assessment.get(
        "key_sentences",
        [],
    ):
        sentence = str(
            item.get(
                "sentence",
                "",
            )
        ).strip()

        if not sentence:
            continue

        translation = item.get(
            "translation",
            "",
        )

        if isinstance(
            translation,
            dict,
        ):
            translation = translation.get(
                "ar",
                "",
            )

        translation = str(
            translation
        ).strip()

        if translation:
            result.append(
                {
                    "sentence": sentence,
                    "translation": translation,
                }
            )

    return result


# ============================================================================
# GET ASSESSMENT
# ============================================================================


@router.get(
    "/lessons/{lesson_id}/assessment",
    response_model=LessonAssessmentResponse,
)
def get_lesson_assessment(
    lesson_id: int,
    conversation_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    lesson, profile, _ = _get_lesson(
        lesson_id,
        current_user,
        db,
    )

    assessment = _load_assessment(
        lesson
    )

    resolved_conversation = (
        _resolve_conversation(
            current_user,
            conversation_id,
            lesson_id,
            profile,
            _load_lesson_curriculum(
                lesson
            ),
            db,
        )
    )

    questions = _public_questions(
        assessment,
        _instruction_language(
            current_user
        ),
    )

    return LessonAssessmentResponse(
        lesson_id=lesson.id,
        passing_score=assessment[
            "passing_score"
        ],
        question_count=len(
            questions
        ),
        questions=questions,
        conversation_ready=bool(
            resolved_conversation
        ),
        key_sentences=_public_key_sentences(
            assessment
        ),
    )


# ============================================================================
# SUBMIT ASSESSMENT
# ============================================================================


@router.post(
    "/lessons/{lesson_id}/assessment",
    response_model=LessonAssessmentResult,
)
def submit_lesson_assessment(
    lesson_id: int,
    data: LessonAssessmentSubmitRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    lesson, profile, lessons = _get_lesson(
        lesson_id,
        current_user,
        db,
    )

    curriculum = _load_lesson_curriculum(
        lesson
    )

    _resolve_conversation(
        current_user,
        data.conversation_id,
        lesson_id,
        profile,
        curriculum,
        db,
    )

    assessment = _load_assessment(
        lesson
    )

    questions = assessment[
        "questions"
    ]

    # ------------------------------------------------------------------------
    # ANSWERS
    # ------------------------------------------------------------------------

    answer_map: dict[str, str] = {}

    for item in data.answers:
        question_id = str(
            item.question_id
        ).strip()

        answer = str(
            item.answer
        ).strip()

        if not question_id or not answer:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Each assessment question "
                    "must have a valid answer."
                ),
            )

        if question_id in answer_map:
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "Each assessment question "
                    "may be answered only once."
                ),
            )

        answer_map[
            question_id
        ] = answer

    question_ids = {
        str(
            item.get(
                "id",
                "",
            )
        ).strip()
        for item in questions
        if str(
            item.get(
                "id",
                "",
            )
        ).strip()
    }

    if set(answer_map) - question_ids:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "The assessment contains "
                "an unknown question id."
            ),
        )

    # ------------------------------------------------------------------------
    # SCORE
    # ------------------------------------------------------------------------

    correct_count = 0

    for question in questions:
        question_id = str(
            question.get(
                "id",
                "",
            )
        ).strip()

        submitted = answer_map.get(
            question_id
        )

        if submitted is None:
            continue

        correct_answer = str(
            question.get(
                "correct_answer",
                "",
            )
        ).strip()

        # Direct ID/text match.
        if submitted == correct_answer:
            correct_count += 1
            continue

        # Option index/text compatibility.
        raw_options = question.get(
            "options",
            [],
        )

        if (
            correct_answer
            and isinstance(
                raw_options,
                list,
            )
        ):
            try:
                option_index = (
                    int(submitted) - 1
                )
            except ValueError:
                option_index = -1

            if (
                0
                <= option_index
                < len(raw_options)
            ):
                option = raw_options[
                    option_index
                ]

                option_text = (
                    option.get("text")
                    if isinstance(
                        option,
                        dict,
                    )
                    else option
                )

                if (
                    str(
                        option_text
                    ).strip()
                    == correct_answer
                ):
                    correct_count += 1
                    continue

        # Accepted alternative answers.
        accepted_answers = question.get(
            "accepted_answers"
        )

        if isinstance(
            accepted_answers,
            list,
        ):
            normalized = {
                str(value)
                .strip()
                .casefold()
                for value in accepted_answers
            }

            if (
                submitted.casefold()
                in normalized
            ):
                correct_count += 1

    total_questions = len(
        questions
    )

    score = (
        round(
            (
                correct_count
                / total_questions
            )
            * 100.0,
            2,
        )
        if total_questions
        else 0.0
    )

    passed = (
        score
        >= assessment[
            "passing_score"
        ]
    )

    # ------------------------------------------------------------------------
    # PROGRESS
    # ------------------------------------------------------------------------

    lesson_ids = [
        item.id
        for item in lessons
    ]

    progress_map = get_progress_map(
        current_user.id,
        profile.id,
        lesson_ids,
        db,
    )

    progress = (
        progress_map.get(
            lesson.id
        )
        or get_or_create_lesson_progress(
            current_user=current_user,
            profile=profile,
            lesson=lesson,
            db=db,
        )
    )

    progress.attempts += 1

    if score > progress.best_score:
        progress.best_score = score

    old_level = profile.level
    new_level = old_level
    level_upgraded = False

    # ------------------------------------------------------------------------
    # PASSED
    # ------------------------------------------------------------------------

    if passed:
        progress.completed = True
        progress.completed_at = (
            datetime.utcnow()
        )

        # Level test.
        if lesson.is_test:
            next_level = get_next_level(
                profile.level
            )

            if next_level is not None:
                profile.level = (
                    next_level
                )

                profile.progress = 0.0

                new_level = next_level
                level_upgraded = True

            else:
                profile.progress = 100.0

        # Normal lesson.
        else:
            progress_map[
                lesson.id
            ] = progress

            normal_lessons = [
                item
                for item in lessons
                if not item.is_test
            ]

            profile.progress = (
                calculate_normal_progress(
                    normal_lessons,
                    progress_map,
                )
            )

    # ------------------------------------------------------------------------
    # FAILED
    # ------------------------------------------------------------------------

    else:
        progress.completed = False

        normal_lessons = [
            item
            for item in lessons
            if not item.is_test
        ]

        profile.progress = (
            calculate_normal_progress(
                normal_lessons,
                progress_map,
            )
        )

    db.commit()

    db.refresh(
        profile
    )

    db.refresh(
        progress
    )

    return LessonAssessmentResult(
        lesson_id=lesson.id,
        score=score,
        passed=passed,
        correct_count=correct_count,
        total_questions=total_questions,
        attempts=progress.attempts,
        best_score=progress.best_score,
        completed=progress.completed,
        level_upgraded=level_upgraded,
        old_level=old_level,
        new_level=new_level,
        new_progress=round(
            profile.progress,
            2,
        ),
    )
