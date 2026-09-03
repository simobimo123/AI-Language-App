from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import AIUsage


DAILY_AI_LIMIT = 200


def extract_token_usage(response) -> tuple[int, int, int]:
    """Read token usage from OpenRouter dicts or compatible response objects."""
    if isinstance(response, dict):
        prompt_tokens = response.get("prompt_tokens", 0) or 0
        completion_tokens = response.get("completion_tokens", 0) or 0
        total_tokens = response.get("total_tokens", 0) or 0
        return (
            int(prompt_tokens),
            int(completion_tokens),
            int(total_tokens),
        )

    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata is None:
        return 0, 0, 0

    prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
    completion_tokens = (
        getattr(usage_metadata, "candidates_token_count", 0) or 0
    )
    total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
    return int(prompt_tokens), int(completion_tokens), int(total_tokens)


def _create_daily_usage_if_missing(
    user_id: int,
    usage_date: date,
    db: Session,
) -> None:
    db.execute(
        insert(AIUsage)
        .values(
            user_id=user_id,
            usage_date=usage_date,
            request_count=0,
            api_call_count=0,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
        )
        .on_conflict_do_nothing(
            index_elements=["user_id", "usage_date"],
        )
    )


def reserve_ai_request(user_id: int, db: Session) -> AIUsage:
    today = date.today()
    _create_daily_usage_if_missing(user_id, today, db)
    db.flush()

    result = db.execute(
        AIUsage.__table__.update()
        .where(
            AIUsage.user_id == user_id,
            AIUsage.usage_date == today,
            AIUsage.request_count < DAILY_AI_LIMIT,
        )
        .values(request_count=AIUsage.request_count + 1)
        .returning(AIUsage.id)
    ).first()

    if result is None:
        db.rollback()
        raise HTTPException(
            status_code=429,
            detail=(
                "You have reached your daily AI usage limit. "
                "Please try again tomorrow."
            ),
        )

    db.commit()
    return db.execute(
        select(AIUsage).where(
            AIUsage.user_id == user_id,
            AIUsage.usage_date == today,
        )
    ).scalar_one()


def get_current_usage(user_id: int, db: Session) -> AIUsage:
    today = date.today()
    usage = db.execute(
        select(AIUsage).where(
            AIUsage.user_id == user_id,
            AIUsage.usage_date == today,
        )
    ).scalar_one_or_none()
    if usage is not None:
        return usage

    _create_daily_usage_if_missing(user_id, today, db)
    db.commit()
    return db.execute(
        select(AIUsage).where(
            AIUsage.user_id == user_id,
            AIUsage.usage_date == today,
        )
    ).scalar_one()


def record_api_usage(
    user_id: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    db: Session,
) -> None:
    usage = get_current_usage(user_id=user_id, db=db)
    usage.api_call_count += 1
    usage.prompt_tokens += max(0, prompt_tokens)
    usage.completion_tokens += max(0, completion_tokens)
    usage.total_tokens += max(0, total_tokens)
    db.commit()
