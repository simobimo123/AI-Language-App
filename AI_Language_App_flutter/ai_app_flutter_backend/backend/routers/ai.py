import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.ai.classification import (
    classify_ai_request,
    get_max_output_tokens,
)
from services.ai.context import (
    build_learning_context,
    build_vocabulary_context,
)
from services.ai.conversation import (
    build_chat_messages,
    get_conversation_history,
)
from services.ai.enrichment.persister import (
    get_or_create_entry_and_sense,
)
from services.ai.enrichment.service import (
    enrich_vocabulary_on_demand,
)
from services.ai.normalization import normalize_language
from services.ai.rate_limit import check_rate_limit
from services.ai.response_stream import (
    sse_event,
    stream_openrouter_response,
)
from services.ai.schemas import ChatRequest
from services.ai.usage import (
    DAILY_AI_LIMIT,
    get_current_usage,
    record_api_usage,
    reserve_ai_request,
)
from services.vocabulary.user_words import save_ai_word_for_user


router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


logger = logging.getLogger(__name__)


MAX_CONVERSATION_MESSAGES = 6


@router.post(
    "/chat"
)
def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    # -----------------------------------------------------
    # 1. Rate limit
    # -----------------------------------------------------

    check_rate_limit(
        current_user.id
    )

    # -----------------------------------------------------
    # 2. Daily quota
    # -----------------------------------------------------

    reserve_ai_request(
        user_id=current_user.id,
        db=db,
    )

    # -----------------------------------------------------
    # 3. Classification
    # -----------------------------------------------------

    (
        classification,
        classifier_prompt_tokens,
        classifier_completion_tokens,
        classifier_total_tokens,
    ) = classify_ai_request(
        message=request.message,
        current_user=current_user,
    )

    # -----------------------------------------------------
    # 4. Record classifier usage
    # -----------------------------------------------------

    if (
        classifier_prompt_tokens
        or classifier_completion_tokens
        or classifier_total_tokens
    ):

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=(
                classifier_prompt_tokens
            ),
            completion_tokens=(
                classifier_completion_tokens
            ),
            total_tokens=(
                classifier_total_tokens
            ),
            db=db,
        )

    logger.info(
        "AI request classification user_id=%s "
        "decision=%s reason=%s",
        current_user.id,
        classification.decision,
        classification.reason,
    )

    # -----------------------------------------------------
    # 5. Block
    # -----------------------------------------------------

    if classification.decision == "BLOCK":

        blocked_message = (
            "هذا الطلب لا يرتبط بشكل كافٍ "
            "بتعلم اللغة. حاول تحويله إلى "
            "سؤال أو تمرين يساعدك على تعلم "
            f"{current_user.learning_language}."
        )

        usage = get_current_usage(
            current_user.id,
            db,
        )

        return StreamingResponse(
            iter(
                [
                    sse_event(
                        {
                            "type": "chunk",
                            "text": blocked_message,
                        }
                    ),
                    sse_event(
                        {
                            "type": "done",
                            "daily_limit": (
                                DAILY_AI_LIMIT
                            ),
                            "daily_used": (
                                usage.request_count
                            ),
                            "daily_remaining": max(
                                0,
                                DAILY_AI_LIMIT
                                - usage.request_count,
                            ),
                        }
                    ),
                ]
            ),
            media_type=(
                "text/event-stream"
            ),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # -----------------------------------------------------
    # 6. Vocabulary
    # -----------------------------------------------------

    vocabulary_context = None

    enrichment_prompt_tokens = 0
    enrichment_completion_tokens = 0
    enrichment_total_tokens = 0

    enrichment_result = None
    saved_word = None

    vocabulary_entry = None
    vocabulary_sense = None

    if (
        classification.needs_vocabulary_enrichment
        and classification.vocabulary_word
    ):

        requested_word = (
            classification
            .vocabulary_word
            .strip()
        )

        try:

            # -------------------------------------------------
            # Create the global vocabulary entry/sense FIRST.
            # -------------------------------------------------

            (
                vocabulary_entry,
                vocabulary_sense,
            ) = get_or_create_entry_and_sense(
                word=requested_word,
                learning_language=(
                    normalize_language(
                        current_user
                        .learning_language
                    )
                ),
                db=db,
            )

            db.commit()

            db.refresh(
                vocabulary_entry
            )

            db.refresh(
                vocabulary_sense
            )

            # -------------------------------------------------
            # Enrich vocabulary.
            # -------------------------------------------------

            (
                vocabulary_context,
                enrichment_prompt_tokens,
                enrichment_completion_tokens,
                enrichment_total_tokens,
                enrichment_result,
            ) = enrich_vocabulary_on_demand(
                word=requested_word,
                current_user=current_user,
                db=db,
            )

            # -------------------------------------------------
            # Save personal user word.
            # -------------------------------------------------

            saved_word = save_ai_word_for_user(
                word=requested_word,
                entry_id=(
                    enrichment_result.entry_id
                    if enrichment_result
                    is not None
                    else vocabulary_entry.id
                ),
                sense_id=(
                    enrichment_result.sense_id
                    if enrichment_result
                    is not None
                    else vocabulary_sense.id
                ),
                current_user=current_user,
                db=db,
            )

            logger.info(
                "AI vocabulary saved "
                "user_id=%s "
                "saved_word_id=%s "
                "word=%s",
                current_user.id,
                saved_word.id,
                saved_word.word,
            )

        except Exception as exc:

            logger.exception(
                "Vocabulary enrichment failed "
                "user_id=%s word=%s: %s",
                current_user.id,
                requested_word,
                exc,
            )

            db.rollback()

            # -------------------------------------------------
            # FALLBACK:
            # Save the requested word even if enrichment fails.
            # -------------------------------------------------

            try:

                if (
                    vocabulary_entry is None
                    or vocabulary_sense is None
                ):

                    (
                        vocabulary_entry,
                        vocabulary_sense,
                    ) = get_or_create_entry_and_sense(
                        word=requested_word,
                        learning_language=(
                            normalize_language(
                                current_user
                                .learning_language
                            )
                        ),
                        db=db,
                    )

                    db.commit()

                    db.refresh(
                        vocabulary_entry
                    )

                    db.refresh(
                        vocabulary_sense
                    )

                saved_word = save_ai_word_for_user(
                    word=requested_word,
                    entry_id=(
                        vocabulary_entry.id
                    ),
                    sense_id=(
                        vocabulary_sense.id
                    ),
                    current_user=current_user,
                    db=db,
                )

                vocabulary_context = (
                    build_vocabulary_context(
                        entry=vocabulary_entry,
                        sense=vocabulary_sense,
                        current_user=current_user,
                        db=db,
                    )
                )

                logger.info(
                    "AI vocabulary fallback save "
                    "successful "
                    "user_id=%s "
                    "saved_word_id=%s "
                    "word=%s",
                    current_user.id,
                    saved_word.id,
                    saved_word.word,
                )

            except Exception as save_exc:

                db.rollback()

                logger.exception(
                    "AI vocabulary fallback save failed "
                    "user_id=%s word=%s: %s",
                    current_user.id,
                    requested_word,
                    save_exc,
                )

    # -----------------------------------------------------
    # 7. Record enrichment usage
    # -----------------------------------------------------

    if (
        enrichment_prompt_tokens
        or enrichment_completion_tokens
        or enrichment_total_tokens
    ):

        record_api_usage(
            user_id=current_user.id,
            prompt_tokens=(
                enrichment_prompt_tokens
            ),
            completion_tokens=(
                enrichment_completion_tokens
            ),
            total_tokens=(
                enrichment_total_tokens
            ),
            db=db,
        )

    # -----------------------------------------------------
    # 8. Learning context
    # -----------------------------------------------------

    learning_context = (
        build_learning_context(
            current_user,
            db,
        )
    )

    # -----------------------------------------------------
    # 9. Conversation history
    # -----------------------------------------------------

    history = (
        get_conversation_history(
            user_id=current_user.id,
            conversation_id=(
                request.conversation_id
            ),
            max_messages=MAX_CONVERSATION_MESSAGES,
            db=db,
        )
    )

    # -----------------------------------------------------
    # 10. OpenAI-compatible chat messages
    # -----------------------------------------------------

    messages = build_chat_messages(
        history=history,
        current_message=request.message,
        vocabulary_context=vocabulary_context,
    )

    # -----------------------------------------------------
    # 11. Final response
    # -----------------------------------------------------

    return StreamingResponse(
        stream_openrouter_response(
            request=request,
            current_user=current_user,
            db=db,
            learning_context=learning_context,
            messages=messages,
            max_output_tokens=get_max_output_tokens(classification),
            max_conversation_messages=MAX_CONVERSATION_MESSAGES,
            classification_decision=classification.decision,
        ),
        media_type=(
            "text/event-stream"
        ),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
