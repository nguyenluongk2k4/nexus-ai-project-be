-- =====================================================
-- PURCHASE MODULE - Database Migration
-- Add balance to users and create transactions table
-- =====================================================

-- 1. Add balance column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS balance DECIMAL(15,2) DEFAULT 0.00;

-- 2. Create transactions table for payment history
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Transaction type and amount
    type VARCHAR(20) NOT NULL CHECK (type IN ('deposit', 'withdraw', 'purchase', 'refund')),
    amount DECIMAL(15,2) NOT NULL,
    balance_before DECIMAL(15,2) NOT NULL DEFAULT 0,
    balance_after DECIMAL(15,2) NOT NULL DEFAULT 0,
    
    -- Payment details (for deposits via SePay/QR)
    transaction_code VARCHAR(100) UNIQUE,  -- NEXUS_ABC123
    payment_method VARCHAR(50) DEFAULT 'sepay_qr',
    bank_reference VARCHAR(200),  -- Reference from bank
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'expired')),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    -- Additional info
    note TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(transaction_code);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at DESC);

-- 3. SePay configuration (optional - can use env instead)
CREATE TABLE IF NOT EXISTS payment_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL DEFAULT 'sepay',
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    qr_template VARCHAR(500),
    webhook_secret VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default SePay config (update with real values)
INSERT INTO payment_config (provider, bank_name, account_number, account_name, qr_template)
VALUES ('sepay', 'MB Bank', '0123456789', 'NEXUS AI PLATFORM', 'https://qr.sepay.vn/img?acc={account}&bank={bank}&amount={amount}&des={content}')
ON CONFLICT DO NOTHING;
