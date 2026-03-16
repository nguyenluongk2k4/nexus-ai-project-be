-- =====================================================
-- COIN PACKAGES - Database Migration
-- Create coin_packages table to replace subscriptions
-- =====================================================

CREATE TABLE IF NOT EXISTS coin_packages (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    coin_amount INTEGER NOT NULL,
    bonus_amount INTEGER DEFAULT 0,
    badge_color VARCHAR(20) DEFAULT '#8B5CF6',
    is_popular BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bảng giá tham khảo (VNĐ) - "Hút máu" theo yêu cầu
-- Chi phí các chức năng: Tree=10, Chat=5, Quiz=2
INSERT INTO coin_packages (id, name, price, coin_amount, bonus_amount, badge_color, is_popular, display_order)
VALUES 
    ('pack_10k', 'Gói Trải Nghiệm', 10000, 30, 0, '#6B7280', FALSE, 1),      -- Tương đương 3 lần gen Tree hoặc 6 lần chat
    ('pack_59k', 'Gói Tiêu Chuẩn', 59000, 180, 20, '#8B5CF6', FALSE, 2),   -- Tương đương 18 lần gen Tree + 2 lần bonus
    ('pack_139k', 'Gói Nâng Cao', 139000, 450, 100, '#F59E0B', TRUE, 3),   -- Giá trị bắt đầu nhỉnh hơn, push user mua gói này
    ('pack_600k', 'Gói Tối Thượng', 600000, 2000, 600, '#EF4444', FALSE, 4) -- Thưởng lớn cho whale
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    price = EXCLUDED.price,
    coin_amount = EXCLUDED.coin_amount,
    bonus_amount = EXCLUDED.bonus_amount,
    badge_color = EXCLUDED.badge_color,
    is_popular = EXCLUDED.is_popular,
    display_order = EXCLUDED.display_order;

-- Chỉnh sửa enum status của Transactions để support loại payment báo mua package
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_type_check;
ALTER TABLE transactions ADD CONSTRAINT transactions_type_check 
    CHECK (type IN ('deposit', 'withdraw', 'purchase', 'refund', 'package_purchase'));
