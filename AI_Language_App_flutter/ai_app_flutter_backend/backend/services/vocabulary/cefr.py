from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import VocabularyCEFRAssessment, VocabularySense
from services.vocabulary.repository import get_sense_or_404


def _clear_selected_cefr_assessments(
    sense_id: int,
    db: Session,
) -> None:

    (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id,
            VocabularyCEFRAssessment
            .is_selected.is_(True),
        )
        .update(
            {
                VocabularyCEFRAssessment
                .is_selected: False,
            },
            synchronize_session=False,
        )
    )


def _select_cefr_assessment(
    sense_id: int,
    assessment_id: int,
    db: Session,
) -> VocabularySense:

    sense = get_sense_or_404(
        sense_id,
        db,
    )

    assessment = (
        db.query(
            VocabularyCEFRAssessment
        )
        .filter(
            VocabularyCEFRAssessment.id
            == assessment_id,
            VocabularyCEFRAssessment
            .vocabulary_sense_id
            == sense_id,
        )
        .first()
    )

    if assessment is None:

        raise HTTPException(
            status_code=404,
            detail="CEFR assessment not found.",
        )

    _clear_selected_cefr_assessments(
        sense_id=sense_id,
        db=db,
    )

    assessment.is_selected = True

    sense.cefr_level = (
        assessment.cefr_level
    )

    db.commit()
    db.refresh(sense)

    return sense

