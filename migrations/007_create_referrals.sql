-- Migration: Add Referral Code to Users & Create Referrals Table
-- Maps to the Supabase schema provided

-- Bước 1: Thêm cột referral_code cho mỗi User (phải là Duy nhất)
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR UNIQUE;

-- Bước 2: Tạo bảng lịch sử Referrals
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Người giới thiệu (chủ nhân của mã code)
    referee_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- Người được giới thiệu (người nhập mã)
    referral_code VARCHAR NOT NULL,                           -- Mã code đã được nhập
    status VARCHAR DEFAULT 'pending',                         -- Trạng thái: pending, completed
    coins_awarded INT DEFAULT 0,                              -- Số xu thưởng đã cấp phát
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

-- Index cho việc tìm kiếm mã theo users
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

-- Index cho việc tìm kiếm mã code nhanh chóng trong lịch sử
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);

-- Index cho việc truy vấn lịch sử giới thiệu của một user
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referee ON referrals(referee_id);
