import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import AIConversationMessage, CourseLesson, LearningProfile, User, UserLessonProgress
from routers.auth import get_current_user
from routers.learning_path import calculate_normal_progress, get_current_lesson, get_next_level, get_progress_map, get_or_create_lesson_progress, sync_learning_content
from schemas import LessonAssessmentQuestion, LessonAssessmentResponse, LessonAssessmentResult, LessonAssessmentSubmitRequest
from services.ai.normalization import normalize_language

router = APIRouter(prefix="/learning", tags=["Lesson Assessment"])
LESSONS_ROOT = Path(__file__).resolve().parents[1] / "data" / "lessons"
MIN_AI_LEARNER_TURNS = 2


def _get_current_profile(current_user: User, db: Session) -> LearningProfile:
    language = normalize_language(current_user.learning_language)
    profile = db.query(LearningProfile).filter(
        LearningProfile.user_id == current_user.id,
        LearningProfile.language == language,
    ).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current learning profile not found.")
    return profile


def _get_lesson(lesson_id: int, current_user: User, db: Session) -> tuple[CourseLesson, LearningProfile, list[CourseLesson]]:
    profile = _get_current_profile(current_user, db)
    try:
        lessons = sync_learning_content(language=profile.language, level=profile.level, db=db)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    lesson = next((item for item in lessons if item.id == lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found in the current curriculum.")

    current_lesson = get_current_lesson(
        lessons=lessons,
        progress_map=get_progress_map(current_user.id, profile.id, [item.id for item in lessons], db),
    )
    if current_lesson is None or current_lesson.id != lesson.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This lesson is currently locked.")
    return lesson, profile, lessons


def _load_assessment(lesson: CourseLesson) -> dict:
    path = LESSONS_ROOT / normalize_language(lesson.language) / str(lesson.level).upper() / f"lesson_{lesson.lesson_order:02d}.json"
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson assessment source file was not found.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lesson assessment source is invalid.") from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Lesson assessment source must be an object.")
    end_test = data.get("end_test")
    if not isinstance(end_test, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This lesson has no final assessment.")
    questions = end_test.get("questions")
    if not isinstance(questions, list) or not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This lesson has no assessment questions.")
    return {
        "passing_score": float(end_test.get("passing_score", lesson.passing_score)),
        "questions": [item for item in questions if isinstance(item, dict)],
    }


def _instruction_language(current_user: User) -> str:
    return normalize_language(current_user.native_language)


def _find_latest_ready_conversation(current_user: User, db: Session) -> str | None:
    rows = db.execute(
        select(AIConversationMessage.conversation_id, AIConversationMessage.role, AIConversationMessage.content)
        .where(
            AIConversationMessage.user_id == current_user.id,
            AIConversationMessage.conversation_id.is_not(None),
        )
        .order_by(AIConversationMessage.created_at.desc(), AIConversationMessage.id.desc())
    ).all()

    grouped: dict[str, dict[str, int]] = {}
    for conversation_id, role, content in rows:
        if not conversation_id:
            continue
        bucket = grouped.setdefault(conversation_id, {"learner": 0, "tutor": 0})
        if role == "user" and content.strip() != "START_LESSON":
            bucket["learner"] += 1
        elif role == "model":
            bucket["tutor"] += 1
        if bucket["learner"] >= MIN_AI_LEARNER_TURNS and bucket["tutor"] >= MIN_AI_LEARNER_TURNS:
            return conversation_id
    return None


def _resolve_conversation(current_user: User, conversation_id: str | None, db: Session) -> str:
    if conversation_id and conversation_id.strip():
        candidate = conversation_id.strip()
        messages = db.execute(
            select(AIConversationMessage.role, AIConversationMessage.content)
            .where(
                AIConversationMessage.user_id == current_user.id,
                AIConversationMessage.conversation_id == candidate,
            )
        ).all()
        learner_turns = sum(1 for role, content in messages if role == "user" and content.strip() != "START_LESSON")
        tutor_turns = sum(1 for role, _ in messages if role == "model")
        if learner_turns >= MIN_AI_LEARNER_TURNS and tutor_turns >= MIN_AI_LEARNER_TURNS:
            return candidate
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Continue the AI lesson and answer at least two tutor prompts before starting the assessment.")

    resolved = _find_latest_ready_conversation(current_user, db)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Continue the AI lesson and answer at least two tutor prompts before starting the assessment.")
    return resolved


def _translation(question: dict, language: str) -> dict:
    translations = question.get("translations")
    if not isinstance(translations, dict):
        return {}
    value = translations.get(language)
    if isinstance(value, dict):
        return value
    value = translations.get("ar")
    return value if isinstance(value, dict) else {}


def _public_questions(assessment: dict, instruction_language: str) -> list[LessonAssessmentQuestion]:
    result = []
    for question in assessment["questions"]:
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            continue
        translation = _translation(question, instruction_language)
        options = translation.get("options") if isinstance(translation.get("options"), list) else []
        public_options = []
        for option in options:
            if not isinstance(option, dict):
                continue
            option_id = str(option.get("id", "")).strip()
            text = str(option.get("text", "")).strip()
            if option_id and text:
                public_options.append({"id": option_id, "text": text})
        result.append(LessonAssessmentQuestion(
            id=question_id,
            order=int(question.get("order", len(result) + 1)),
            type=str(question.get("type", "multiple_choice")),
            question=str(translation.get("question", "")).strip(),
            options=public_options,
        ))
    result.sort(key=lambda item: item.order)
    return result


@router.get("/lessons/{lesson_id}/assessment", response_model=LessonAssessmentResponse)
def get_lesson_assessment(
    lesson_id: int,
    conversation_id: str | None = Query(default=None, min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson, _, _ = _get_lesson(lesson_id, current_user, db)
    resolved_conversation = _resolve_conversation(current_user, conversation_id, db)
    assessment = _load_assessment(lesson)
    questions = _public_questions(assessment, _instruction_language(current_user))
    return LessonAssessmentResponse(
        lesson_id=lesson.id,
        passing_score=assessment["passing_score"],
        question_count=len(questions),
        questions=questions,
        conversation_ready=bool(resolved_conversation),
    )


@router.post("/lessons/{lesson_id}/assessment", response_model=LessonAssessmentResult)
def submit_lesson_assessment(
    lesson_id: int,
    data: LessonAssessmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson, profile, lessons = _get_lesson(lesson_id, current_user, db)
    _resolve_conversation(current_user, data.conversation_id, db)
    assessment = _load_assessment(lesson)
    questions = assessment["questions"]

    answer_map = {item.question_id.strip(): item.answer.strip() for item in data.answers if item.question_id.strip() and item.answer.strip()}
    if len(answer_map) != len(data.answers):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each assessment question may be answered only once.")

    question_ids = {str(item.get("id", "")).strip() for item in questions if str(item.get("id", "")).strip()}
    if set(answer_map) - question_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The assessment contains an unknown question id.")

    correct_count = 0
    for question in questions:
        question_id = str(question.get("id", "")).strip()
        if answer_map.get(question_id) is not None and answer_map.get(question_id) == str(question.get("correct_answer", "")).strip():
            correct_count += 1

    total_questions = len(questions)
    score = round((correct_count / total_questions) * 100.0, 2) if total_questions else 0.0
    passed = score >= assessment["passing_score"]
    lesson_ids = [item.id for item in lessons]
    progress_map = get_progress_map(current_user.id, profile.id, lesson_ids, db)
    progress = progress_map.get(lesson.id) or get_or_create_lesson_progress(current_user=current_user, profile=profile, lesson=lesson, db=db)
    progress.attempts += 1
    if score > progress.best_score:
        progress.best_score = score

    old_level = profile.level
    new_level = old_level
    level_upgraded = False
    if passed:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        if lesson.is_test:
            next_level = get_next_level(profile.level)
            if next_level is not None:
                profile.level = next_level
                profile.progress = 0.0
                new_level = next_level
                level_upgraded = True
            else:
                profile.progress = 100.0
        else:
            progress_map[lesson.id] = progress
            normal_lessons = [item for item in lessons if not item.is_test]
            profile.progress = calculate_normal_progress(normal_lessons, progress_map)
    else:
        progress.completed = False
        normal_lessons = [item for item in lessons if not item.is_test]
        profile.progress = calculate_normal_progress(normal_lessons, progress_map)

    db.commit()
    db.refresh(profile)
    db.refresh(progress)
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
        new_progress=round(profile.progress, 2),
    )
