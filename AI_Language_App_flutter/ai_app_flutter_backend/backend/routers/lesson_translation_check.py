import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import CourseLesson, LearningProfile, User, UserLessonProgress
from routers.auth import get_current_user
from routers.lesson_ai import _lesson_target_sentences, _load_lesson_curriculum
from services.ai.client import AI_MODEL
from services.ai.normalization import normalize_language, normalize_level
from services.ai.provider import provider
from services.ai.rate_limit import check_rate_limit
from services.ai.usage import record_api_usage, reserve_ai_request

router = APIRouter(prefix="/learning", tags=["Lesson Translation Check"])
logger = logging.getLogger(__name__)

TRANSLATION_CHECK_MODEL = AI_MODEL
TRANSLATION_CHECK_MAX_OUTPUT_TOKENS = 500


class TranslationCheckAnswer(BaseModel):
    question_id: str = Field(min_length=1, max_length=100)
    answer: str = Field(min_length=1, max_length=1000)


class TranslationCheckSubmitRequest(BaseModel):
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)
    answers: list[TranslationCheckAnswer] = Field(min_length=1, max_length=20)


def _get_lesson_and_profile(lesson_id: int, current_user: User, db: Session):
    lesson = db.get(CourseLesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

    target_language = normalize_language(current_user.learning_language)
    if normalize_language(lesson.language) != target_language:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson does not belong to your learning language.",
        )

    profile = db.execute(
        select(LearningProfile).where(
            LearningProfile.user_id == current_user.id,
            LearningProfile.language == target_language,
        )
    ).scalar_one_or_none()
    if profile is None or normalize_level(profile.level) != normalize_level(lesson.level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This lesson is not part of your current learning level.",
        )

    return lesson, profile


def _get_progress(
    user_id: int,
    profile_id: int,
    lesson_id: int,
    db: Session,
) -> UserLessonProgress:
    progress = db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
    ).scalar_one_or_none()
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete the AI lesson practice before starting the translation check.",
        )
    return progress


def _resolve_conversation(
    user_id: int,
    profile_id: int,
    lesson_id: int,
    conversation_id: str | None,
    curriculum: dict,
    db: Session,
) -> tuple[str, UserLessonProgress]:
    if not conversation_id or not conversation_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Continue the lesson conversation first.",
        )

    candidate = conversation_id.strip()
    if not candidate.startswith(f"lesson_{lesson_id}_"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid lesson conversation.")

    progress = _get_progress(user_id, profile_id, lesson_id, db)
    state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
    if state.get("conversation_id") != candidate:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This lesson conversation is no longer active.")

    target_ids = {item["id"] for item in _lesson_target_sentences(curriculum)}
    practiced_ids = {
        str(value).strip()
        for value in state.get("practiced_sentence_ids", [])
        if str(value).strip()
    } if isinstance(state.get("practiced_sentence_ids", []), list) else set()

    if not target_ids or not target_ids.issubset(practiced_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete all required target sentences in the AI lesson first.",
        )

    return candidate, progress


def _translation_sentences(curriculum: dict) -> list[dict[str, str]]:
    return _lesson_target_sentences(curriculum)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("AI returned an invalid translation evaluation.") from exc
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise RuntimeError("AI returned an invalid translation evaluation.")
    return value


def _evaluation_prompt(
    native_language: str,
    target_language: str,
    sentences: list[dict[str, str]],
    answers: list[TranslationCheckAnswer],
) -> str:
    answer_map = {item.question_id.strip(): item.answer.strip() for item in answers}
    pairs = [
        {
            "id": item["id"],
            "source": item["sentence"],
            "learner_translation": answer_map.get(item["id"], ""),
        }
        for item in sentences
    ]
    payload = json.dumps(pairs, ensure_ascii=False, separators=(",", ":"))

    return f"""
Evaluate a language-learning translation check.

Target language: {target_language}
Learner native language: {native_language}

For each item, decide whether the learner's translation correctly conveys the meaning of the target-language sentence in the learner's native language.
Do NOT require literal word-for-word matching. Accept natural alternative wording, grammar variations, punctuation differences, articles, and reasonable synonyms when the meaning is preserved.
Do not translate the answers yourself for the learner and do not invent missing information.
A materially wrong meaning is incorrect. A blank or unrelated answer is incorrect.

Return JSON only in this exact shape:
{{"score":0,"passed":false,"results":[{{"id":"1","correct":false}}]}}

The pass threshold is 80 percent.

Items:
{payload}
"""


@router.get("/lessons/{lesson_id}/translation-check")
def get_translation_check(
    lesson_id: int,
    conversation_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson, profile = _get_lesson_and_profile(lesson_id, current_user, db)
    curriculum = _load_lesson_curriculum(lesson)
    resolved, _ = _resolve_conversation(
        current_user.id,
        profile.id,
        lesson_id,
        conversation_id,
        curriculum,
        db,
    )
    sentences = _translation_sentences(curriculum)
    if not sentences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This lesson has no translation check sentences.",
        )

    return {
        "lesson_id": lesson.id,
        "conversation_id": resolved,
        "native_language": normalize_language(current_user.native_language),
        "target_language": normalize_language(current_user.learning_language),
        "question_count": len(sentences),
        "questions": sentences,
        "passing_score": 80.0,
    }


@router.post("/lessons/{lesson_id}/translation-check")
def submit_translation_check(
    lesson_id: int,
    data: TranslationCheckSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lesson, profile = _get_lesson_and_profile(lesson_id, current_user, db)
    curriculum = _load_lesson_curriculum(lesson)
    conversation_id, progress = _resolve_conversation(
        current_user.id,
        profile.id,
        lesson_id,
        data.conversation_id,
        curriculum,
        db,
    )
    sentences = _translation_sentences(curriculum)
    if not sentences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This lesson has no translation check sentences.",
        )

    sentence_ids = {item["id"] for item in sentences}
    submitted_ids = [item.question_id.strip() for item in data.answers]
    if len(set(submitted_ids)) != len(submitted_ids) or set(submitted_ids) != sentence_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Answer every translation question exactly once.",
        )

    check_rate_limit(current_user.id)
    reserve_ai_request(user_id=current_user.id, db=db)

    try:
        response = provider.generate_text(
            model=TRANSLATION_CHECK_MODEL,
            prompt=_evaluation_prompt(
                native_language=normalize_language(current_user.native_language),
                target_language=normalize_language(current_user.learning_language),
                sentences=sentences,
                answers=data.answers,
            ),
            max_output_tokens=TRANSLATION_CHECK_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        )
        evaluation = _extract_json(response.text)
        results = evaluation.get("results")
        if not isinstance(results, list):
            raise RuntimeError("AI returned an invalid result list.")

        correct_map = {
            str(item.get("id", "")): bool(item.get("correct", False))
            for item in results
            if isinstance(item, dict)
        }
        if set(correct_map) != sentence_ids:
            raise RuntimeError("AI did not evaluate every translation question.")

        correct_count = sum(1 for value in correct_map.values() if value)
        score = round((correct_count / len(sentences)) * 100.0, 2)
        passed = score >= 80.0

        state = progress.practice_state if isinstance(progress.practice_state, dict) else {}
        progress.practice_state = {
            **state,
            "translation_check_passed": passed,
            "translation_check_score": score,
        }

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            db=db,
        )
        db.commit()

        return {
            "lesson_id": lesson.id,
            "conversation_id": conversation_id,
            "score": score,
            "passed": passed,
            "correct_count": correct_count,
            "total_questions": len(sentences),
            "results": [
                {"id": item["id"], "correct": correct_map[item["id"]]}
                for item in sentences
            ],
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Translation check failed user_id=%s lesson_id=%s: %s",
            current_user.id,
            lesson_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation check is temporarily unavailable.",
        ) from exc
