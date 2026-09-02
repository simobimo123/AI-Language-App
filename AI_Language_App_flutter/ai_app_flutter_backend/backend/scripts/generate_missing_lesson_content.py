"""Generate missing lesson content offline and store it in PostgreSQL.

Examples:
    python scripts/generate_missing_lesson_content.py --language de --level PRE_A1
    python scripts/generate_missing_lesson_content.py --language de --level PRE_A1 --limit 1

Existing READY content is skipped unless --force is supplied.
This script is intentionally separate from normal user requests so lesson
creation does not consume AI calls at runtime.
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import select

from database import SessionLocal
from models import CourseLesson, LessonContent
from services.ai.client import AI_MODEL
from services.ai.lesson_generator import generate_lesson_content
from services.ai.normalization import normalize_language, normalize_level

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate missing lesson content.")
    parser.add_argument("--language", required=True)
    parser.add_argument("--level", required=True)
    parser.add_argument("--instruction-language", default="ar")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    language = normalize_language(args.language)
    level = normalize_level(args.level)
    instruction_language = normalize_language(args.instruction_language)

    if level is None:
        raise SystemExit("Unsupported CEFR level.")

    db = SessionLocal()
    generated_count = 0
    skipped_count = 0
    failed_count = 0

    try:
        lessons = db.execute(
            select(CourseLesson)
            .where(
                CourseLesson.language == language,
                CourseLesson.level == level,
            )
            .order_by(CourseLesson.lesson_order.asc())
        ).scalars().all()

        if args.limit > 0:
            lessons = lessons[:args.limit]

        if not lessons:
            raise SystemExit(
                f"No lessons found for language={language} level={level}. "
                "Start the backend once so curriculum seeding can run."
            )

        logger.info(
            "Found %s lessons for %s/%s using model=%s",
            len(lessons), language, level, AI_MODEL,
        )

        for lesson in lessons:
            existing = db.execute(
                select(LessonContent).where(
                    LessonContent.lesson_id == lesson.id,
                    LessonContent.instruction_language == instruction_language,
                )
            ).scalar_one_or_none()

            if existing and existing.status == "READY" and not args.force:
                skipped_count += 1
                logger.info("SKIP lesson_id=%s already READY", lesson.id)
                continue

            if existing is None:
                existing = LessonContent(
                    lesson_id=lesson.id,
                    instruction_language=instruction_language,
                    status="GENERATING",
                    content={},
                    generator_model=AI_MODEL,
                )
                db.add(existing)
            else:
                existing.status = "GENERATING"
                existing.generation_error = None
                existing.generator_model = AI_MODEL

            db.commit()

            try:
                generated, prompt_tokens, completion_tokens, total_tokens = (
                    generate_lesson_content(
                        lesson=lesson,
                        instruction_language=instruction_language,
                    )
                )

                existing.content = generated.model_dump()
                existing.status = "READY"
                existing.generator_model = AI_MODEL
                existing.generation_error = None
                existing.version = (existing.version or 0) + 1
                db.commit()

                generated_count += 1
                logger.info(
                    "READY lesson_id=%s order=%s tokens=%s/%s/%s",
                    lesson.id,
                    lesson.lesson_order,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                )

            except Exception as exc:
                db.rollback()
                failed = db.get(LessonContent, existing.id)
                if failed is not None:
                    failed.status = "FAILED"
                    failed.generation_error = str(exc)[:4000]
                    db.commit()
                failed_count += 1
                logger.exception("FAILED lesson_id=%s", lesson.id)

        logger.info(
            "Finished: generated=%s skipped=%s failed=%s",
            generated_count,
            skipped_count,
            failed_count,
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
