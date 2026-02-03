import asyncio
from sqlalchemy import text
from shared.database.connection import async_session_maker

async def migrate():
    async with async_session_maker() as session:
        print("Checking users table columns...")
        
        # Add role if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'member';
        """))
        
        # Add points if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS points BIGINT DEFAULT 0;
        """))
        
        # Add balance if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS balance NUMERIC DEFAULT 0;
        """))
        
        # Add subscription_tier if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free';
        """))
        
        # Add subscription_expires_at if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP;
        """))
        
        # Add is_admin if missing
        await session.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
        """))
        
        # Make password_hash nullable
        await session.execute(text("""
            ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
        """))
        
        # Remove old role column if exists
        await session.execute(text("""
            ALTER TABLE users DROP COLUMN IF EXISTS role;
        """))
        
        await session.commit()
        print("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
