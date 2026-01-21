"""
Add scheduled_time column to timeline_items table

Run this manually:
python -m scripts.add_scheduled_time_column
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres.eqbkjsqkuoobklxbwnkf:DPsgP-0912@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

async def add_column():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Add scheduled_time column
            await session.execute(
                text("""
                    ALTER TABLE timeline_items 
                    ADD COLUMN IF NOT EXISTS scheduled_time VARCHAR(5);
                """)
            )
            
            # Set default value for existing rows
            await session.execute(
                text("""
                    UPDATE timeline_items 
                    SET scheduled_time = '08:00' 
                    WHERE scheduled_time IS NULL;
                """)
            )
            
            await session.commit()
            print("✅ Successfully added scheduled_time column!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_column())
