"""
Migration: Add source_resource fields to quiz_questions table
Run: python run_quiz_migration_v2.py
"""

import asyncio
from sqlalchemy import text
from shared.database import get_db_context

async def run_migration():
    """
    Add source_resource_id and source_resource_title columns to quiz_questions.
    - source_resource_id is NULLABLE UUID (optional FK to learning_resources)
    - source_resource_title is cached title for display
    """
    
    async with get_db_context() as db:
        # Check if column exists
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'quiz_questions' 
            AND column_name = 'source_resource_id'
        """))
        
        if result.fetchone():
            print("✅ source_resource columns already exist")
            return
        
        print("🔧 Adding source_resource_id and source_resource_title columns...")
        
        # Add columns without FK first (for flexibility - not all questions have resources)
        await db.execute(text("""
            ALTER TABLE quiz_questions 
            ADD COLUMN IF NOT EXISTS source_resource_id UUID,
            ADD COLUMN IF NOT EXISTS source_resource_title VARCHAR(500)
        """))
        
        print("🔧 Adding foreign key constraint (nullable)...")
        
        # Add FK constraint - SET NULL on delete since it's optional
        try:
            await db.execute(text("""
                ALTER TABLE quiz_questions 
                ADD CONSTRAINT fk_quiz_question_resource 
                FOREIGN KEY (source_resource_id) 
                REFERENCES learning_resources(id) 
                ON DELETE SET NULL
            """))
            print("✅ FK constraint added")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✅ FK constraint already exists")
            else:
                print(f"⚠️ FK constraint not added (non-fatal): {e}")
                # This is OK - table works without FK, just less strict
        
        await db.commit()
        print("✅ Migration completed!")


if __name__ == "__main__":
    asyncio.run(run_migration())
