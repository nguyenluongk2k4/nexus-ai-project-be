
import asyncio
from sqlalchemy import text
from shared.database.connection import async_session_maker

async def run_migration():
    print("Running Add Attachments Migration...")
    
    async with async_session_maker() as session:
        # Add attachments column to messages table
        print("Adding attachments column to messages table...")
        try:
            await session.execute(text("""
                ALTER TABLE messages ADD COLUMN IF NOT EXISTS attachments JSONB DEFAULT '[]'::jsonb
            """))
            print("   Attachments column added/exists")
        except Exception as e:
            print(f"   Attachments column error: {e}")
        
        await session.commit()
    
    print("\nAdd Attachments Migration completed!")


if __name__ == "__main__":
    asyncio.run(run_migration())
