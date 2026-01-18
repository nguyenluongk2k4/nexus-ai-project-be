"""
Run Purchase Module Migration
Execute this script to add balance column and create transactions table
"""

import asyncio
from sqlalchemy import text
from shared.database.connection import async_session_maker


async def run_migration():
    print("🚀 Running Purchase Module Migration...")
    
    async with async_session_maker() as session:
        # 1. Add balance column to users table
        print("📦 Adding balance column to users table...")
        try:
            await session.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS balance DECIMAL(15,2) DEFAULT 0.00
            """))
            print("   ✅ Balance column added/exists")
        except Exception as e:
            print(f"   ⚠️ Balance column: {e}")
        
        # 2. Create transactions table
        print("📦 Creating transactions table...")
        try:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    type VARCHAR(20) NOT NULL CHECK (type IN ('deposit', 'withdraw', 'purchase', 'refund')),
                    amount DECIMAL(15,2) NOT NULL,
                    balance_before DECIMAL(15,2) NOT NULL DEFAULT 0,
                    balance_after DECIMAL(15,2) NOT NULL DEFAULT 0,
                    transaction_code VARCHAR(100) UNIQUE,
                    payment_method VARCHAR(50) DEFAULT 'sepay_qr',
                    bank_reference VARCHAR(200),
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'expired')),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    note TEXT,
                    metadata JSONB DEFAULT '{}'
                )
            """))
            print("   ✅ Transactions table created/exists")
        except Exception as e:
            print(f"   ⚠️ Transactions table: {e}")
        
        # 3. Create indexes
        print("📦 Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(transaction_code)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at DESC)"
        ]
        for idx_sql in indexes:
            try:
                await session.execute(text(idx_sql))
            except Exception as e:
                print(f"   ⚠️ Index: {e}")
        print("   ✅ Indexes created/exist")
        
        await session.commit()
    
    print("\n✅ Purchase Module Migration completed!")


if __name__ == "__main__":
    asyncio.run(run_migration())
