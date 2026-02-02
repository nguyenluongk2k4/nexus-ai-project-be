-- ===================================
-- Coins System Migration
-- Date: 2026-02-01
-- ===================================

-- 1. User Coins Balance Table
CREATE TABLE IF NOT EXISTS user_coins (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    current_coins INTEGER NOT NULL DEFAULT 0,
    lifetime_earned INTEGER NOT NULL DEFAULT 0,
    lifetime_spent INTEGER NOT NULL DEFAULT 0,
    last_refresh_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE user_coins IS 'Stores coins balance for each user (virtual currency)';
COMMENT ON COLUMN user_coins.current_coins IS 'Current available coins';
COMMENT ON COLUMN user_coins.lifetime_earned IS 'Total coins earned from missions/referrals';
COMMENT ON COLUMN user_coins.lifetime_spent IS 'Total coins spent on services';

-- 2. Coin Transactions Log Table
CREATE TABLE IF NOT EXISTS coin_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    service_type VARCHAR(50),
    reference_id UUID,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON coin_transactions(user_id, created_at DESC);

COMMENT ON TABLE coin_transactions IS 'Audit log for all coin transactions';
COMMENT ON COLUMN coin_transactions.amount IS 'Positive = earn, Negative = spend';
COMMENT ON COLUMN coin_transactions.transaction_type IS 'subscription, mission, referral, service, admin';
COMMENT ON COLUMN coin_transactions.service_type IS 'ai_chat, quiz_gen, summarize, etc.';

-- 3. Missions Table
CREATE TABLE IF NOT EXISTS missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    mission_type VARCHAR(50) NOT NULL,
    coin_reward INTEGER NOT NULL,
    is_repeatable BOOLEAN DEFAULT FALSE,
    repeat_frequency VARCHAR(20),
    max_per_period INTEGER,
    requirements JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    icon VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE missions IS 'Available missions for users to earn coins';
COMMENT ON COLUMN missions.mission_type IS 'invite_friend, update_profile, purchase_plan, try_service, etc.';
COMMENT ON COLUMN missions.repeat_frequency IS 'daily, weekly, monthly for repeatable missions';

-- 4. User Missions Progress Table
CREATE TABLE IF NOT EXISTS user_missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'in_progress',
    progress JSONB DEFAULT '{}',
    completed_at TIMESTAMP,
    coins_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_missions_user ON user_missions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_missions_mission ON user_missions(mission_id);

COMMENT ON TABLE user_missions IS 'Tracks user progress on missions';
COMMENT ON COLUMN user_missions.status IS 'in_progress, completed';
COMMENT ON COLUMN user_missions.progress IS 'JSON data for tracking mission progress';

-- 5. Referrals Table
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    referral_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    coins_awarded INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);

COMMENT ON TABLE referrals IS 'Tracks referral relationships and rewards';
COMMENT ON COLUMN referrals.status IS 'pending, registered, completed, rewarded';
COMMENT ON COLUMN referrals.coins_awarded IS 'Total coins awarded to referrer';

-- ===================================
-- Initial Data Seeding
-- ===================================

-- Seed initial missions
INSERT INTO missions (id, name, description, mission_type, coin_reward, is_repeatable, repeat_frequency, max_per_period, icon) VALUES
    (gen_random_uuid(), 'Mời bạn bè', 'Mời bạn bè đăng ký tài khoản thành công', 'invite_friend', 50, TRUE, NULL, NULL, '👥'),
    (gen_random_uuid(), 'Cập nhật thông tin', 'Hoàn thiện profile với avatar và tên đầy đủ', 'update_profile', 10, FALSE, NULL, NULL, '✏️'),
    (gen_random_uuid(), 'Mua gói dịch vụ', 'Mua bất kỳ gói paid nào (Pro/Premium)', 'purchase_plan', 100, FALSE, NULL, NULL, '💎'),
    (gen_random_uuid(), 'Trải nghiệm AI Chat', 'Sử dụng AI chatbot lần đầu tiên', 'try_service', 20, FALSE, NULL, NULL, '💬'),
    (gen_random_uuid(), 'Hoàn thành Quiz', 'Hoàn thành 1 quiz bất kỳ', 'complete_quiz', 15, TRUE, 'daily', 3, '📝'),
    (gen_random_uuid(), 'Chia sẻ mạng xã hội', 'Chia sẻ ứng dụng lên Facebook/Twitter', 'share_social', 30, TRUE, 'weekly', 1, '📢')
ON CONFLICT DO NOTHING;

-- ===================================
-- Rollback Script (if needed)
-- ===================================
/*
DROP TABLE IF EXISTS user_missions CASCADE;
DROP TABLE IF EXISTS missions CASCADE;
DROP TABLE IF EXISTS referrals CASCADE;
DROP TABLE IF EXISTS coin_transactions CASCADE;
DROP TABLE IF EXISTS user_coins CASCADE;
*/
