from sqlalchemy import inspect, text

from database import engine


def ensure_lesson_curriculum() -> None:
    """Create normalized curriculum tables used by AI teaching and practice."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())

        if "lesson_targets" not in tables:
            connection.execute(text("""
                CREATE TABLE lesson_targets (
                    id SERIAL PRIMARY KEY,
                    lesson_id INTEGER NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
                    target_key VARCHAR(100) NOT NULL,
                    target_order INTEGER NOT NULL,
                    goal TEXT NOT NULL,
                    required BOOLEAN NOT NULL DEFAULT TRUE,
                    cefr_level VARCHAR(10),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_lesson_target_key UNIQUE (lesson_id, target_key),
                    CONSTRAINT uq_lesson_target_order UNIQUE (lesson_id, target_order)
                )
            """))
            connection.execute(text("CREATE INDEX ix_lesson_targets_lesson_id ON lesson_targets (lesson_id)"))

        if "lesson_target_patterns" not in tables:
            connection.execute(text("""
                CREATE TABLE lesson_target_patterns (
                    id SERIAL PRIMARY KEY,
                    target_id INTEGER NOT NULL REFERENCES lesson_targets(id) ON DELETE CASCADE,
                    pattern TEXT NOT NULL,
                    pattern_type VARCHAR(30) NOT NULL DEFAULT 'expected',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_lesson_target_pattern UNIQUE (target_id, pattern)
                )
            """))
            connection.execute(text("CREATE INDEX ix_lesson_target_patterns_target_id ON lesson_target_patterns (target_id)"))

        if "lesson_practice_scenarios" not in tables:
            connection.execute(text("""
                CREATE TABLE lesson_practice_scenarios (
                    id SERIAL PRIMARY KEY,
                    lesson_id INTEGER NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
                    scenario_key VARCHAR(100) NOT NULL,
                    scenario_order INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    context TEXT NOT NULL,
                    instructions TEXT,
                    target_ids JSON NOT NULL DEFAULT '[]'::json,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_lesson_practice_scenario_key UNIQUE (lesson_id, scenario_key)
                )
            """))
            connection.execute(text("CREATE INDEX ix_lesson_practice_scenarios_lesson_id ON lesson_practice_scenarios (lesson_id)"))

        if "user_lesson_target_progress" not in tables:
            connection.execute(text("""
                CREATE TABLE user_lesson_target_progress (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    learning_profile_id INTEGER NOT NULL REFERENCES learning_profiles(id) ON DELETE CASCADE,
                    lesson_id INTEGER NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
                    target_id INTEGER NOT NULL REFERENCES lesson_targets(id) ON DELETE CASCADE,
                    teaching_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    practice_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    teaching_attempts INTEGER NOT NULL DEFAULT 0,
                    practice_attempts INTEGER NOT NULL DEFAULT 0,
                    teaching_successes INTEGER NOT NULL DEFAULT 0,
                    practice_successes INTEGER NOT NULL DEFAULT 0,
                    mastery_confidence FLOAT NOT NULL DEFAULT 0,
                    last_evidence TEXT,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_user_lesson_target_progress UNIQUE (user_id, lesson_id, target_id)
                )
            """))
            connection.execute(text("CREATE INDEX ix_user_lesson_target_progress_user_id ON user_lesson_target_progress (user_id)"))
            connection.execute(text("CREATE INDEX ix_user_lesson_target_progress_lesson_id ON user_lesson_target_progress (lesson_id)"))
            connection.execute(text("CREATE INDEX ix_user_lesson_target_progress_target_id ON user_lesson_target_progress (target_id)"))


def main() -> None:
    ensure_lesson_curriculum()
    print("Lesson curriculum schema is ready.")


ensure_lesson_curriculum()
