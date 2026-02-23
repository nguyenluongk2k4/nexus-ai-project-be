-- =============================================================
-- Migration: New Referral Code Algorithm (Hybrid: UUID Prefix + Random)
-- Chạy 1 lần trên Supabase SQL Editor
-- =============================================================

-- Bước 2: Helper function để sinh random string (8 chars Base62 style)
-- Character set: 0-9, A-Z, a-z (62 chars)
CREATE OR REPLACE FUNCTION gen_random_base62(length int DEFAULT 8)
RETURNS TEXT AS $$
DECLARE
    alphabet TEXT := '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
    result TEXT := '';
    i INT;
BEGIN
    FOR i IN 1..length LOOP
        result := result || substr(alphabet, floor(random() * 62)::int + 1, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- Bước 3: Tạo function combine để generate full code (hex prefix + random base62)
CREATE OR REPLACE FUNCTION gen_referral_code_v2_full(uid UUID)
RETURNS TEXT AS $$
DECLARE
    hex_prefix TEXT;
    uuid_str TEXT;
    random_suffix TEXT;
BEGIN
    -- Get first 8 chars of UUID hex
    uuid_str := replace(uid::text, '-', '');
    hex_prefix := substring(uuid_str, 1, 8);
    
    -- Generate 8 chars random Base62
    random_suffix := gen_random_base62(8);
    
    -- Combine: XXXXXXXX + YYYYYYYY
    RETURN hex_prefix || random_suffix;
END;
$$ LANGUAGE plpgsql;


-- Bước 4: Backfill user cũ có null referral_code
-- Chỉ backfill những user chưa có code
UPDATE users 
SET referral_code = gen_referral_code_v2_full(users.id)
WHERE referral_code IS NULL;

-- Bước 5: Verify kết quả
SELECT 
    count(*) AS total_users,
    count(referral_code) AS has_code,
    count(DISTINCT referral_code) AS unique_codes,
    count(*) FILTER (WHERE referral_code IS NULL) AS missing_code,
    min(length(referral_code)) AS min_length,
    max(length(referral_code)) AS max_length
FROM users;

-- Bước 6: Sample codes
SELECT id, referral_code, length(referral_code) as code_length 
FROM users 
WHERE referral_code IS NOT NULL
LIMIT 10;
