-- =====================================================
-- SUBSCRIPTION PLANS - Database Migration
-- Add subscription tier to users and create plans table
-- =====================================================

-- 1. Add subscription columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP;

-- 2. Create subscription_plans table
CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    price_monthly DECIMAL(15,2) NOT NULL DEFAULT 0,
    price_yearly DECIMAL(15,2) NOT NULL DEFAULT 0,
    features JSONB DEFAULT '[]',
    badge_color VARCHAR(20) DEFAULT '#8B5CF6',
    is_popular BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Insert sample plans (prices in VND - you can update later)
INSERT INTO subscription_plans (id, name, description, price_monthly, price_yearly, features, badge_color, is_popular, display_order)
VALUES 
    ('free', 'Free', 'Gói cơ bản miễn phí', 0, 0, 
     '["5 câu hỏi/ngày", "Trả lời cơ bản", "Hỗ trợ cộng đồng"]'::jsonb, 
     '#6B7280', FALSE, 0),
    
    ('pro', 'Pro', 'Dành cho người dùng cá nhân', 1000, 10000, 
     '["50 câu hỏi/ngày", "Trả lời nâng cao", "Ưu tiên xử lý", "Lưu lịch sử không giới hạn", "Hỗ trợ email"]'::jsonb, 
     '#8B5CF6', FALSE, 1),
    
    ('premium', 'Premium', 'Trải nghiệm tốt nhất', 1500, 15000, 
     '["Không giới hạn câu hỏi", "AI thông minh nhất", "Xử lý siêu nhanh", "Tính năng độc quyền", "Hỗ trợ 24/7", "Truy cập sớm tính năng mới"]'::jsonb, 
     '#F59E0B', TRUE, 2),
    
    ('business', 'Business', 'Dành cho doanh nghiệp', 2000, 20000, 
     '["Tất cả tính năng Premium", "API truy cập", "Quản lý team", "Báo cáo chi tiết", "Đào tạo 1-1", "Account Manager riêng", "SLA 99.9%"]'::jsonb, 
     '#10B981', FALSE, 3)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price_monthly = EXCLUDED.price_monthly,
    price_yearly = EXCLUDED.price_yearly,
    features = EXCLUDED.features,
    badge_color = EXCLUDED.badge_color,
    is_popular = EXCLUDED.is_popular,
    display_order = EXCLUDED.display_order;

-- 4. Create subscription_transactions table (to track purchases)
CREATE TABLE IF NOT EXISTS subscription_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id VARCHAR(20) NOT NULL REFERENCES subscription_plans(id),
    billing_cycle VARCHAR(10) NOT NULL CHECK (billing_cycle IN ('monthly', 'yearly')),
    amount DECIMAL(15,2) NOT NULL,
    starts_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_sub_trans_user ON subscription_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_sub_trans_expires ON subscription_transactions(expires_at);
