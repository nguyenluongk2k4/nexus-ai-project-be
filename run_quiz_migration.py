"""
Run Quiz Module Migration
Creates quiz_attempts, quiz_questions, quiz_answers tables
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.database import get_db_context


MIGRATION_SQL = """
-- Quiz Attempts
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES user_skill_nodes(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'generating',
    score FLOAT,
    correct_count INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    config_snapshot JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_node ON quiz_attempts(node_id);

-- Quiz Questions
CREATE TABLE IF NOT EXISTS quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_option_index INTEGER NOT NULL,
    explanation TEXT,
    topic_tag VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_attempt ON quiz_questions(attempt_id);

-- Quiz Answers
CREATE TABLE IF NOT EXISTS quiz_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    selected_option_index INTEGER NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    time_taken_seconds INTEGER,
    answered_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_answers_question ON quiz_answers(question_id);
"""


async def run_migration():
    print("🚀 Running Quiz Module Migration...")
    
    async with get_db_context() as db:
        # Execute migration SQL
        from sqlalchemy import text
        
        # Split and execute statements
        statements = [s.strip() for s in MIGRATION_SQL.split(';') if s.strip()]
        
        for stmt in statements:
            try:
                await db.execute(text(stmt))
                print(f"✅ Executed: {stmt[:50]}...")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"⏭️ Skipped (exists): {stmt[:50]}...")
                else:
                    print(f"⚠️ Error: {e}")
        
        await db.commit()
    
    print("✅ Quiz Module Migration completed!")


if __name__ == "__main__":
    asyncio.run(run_migration())
