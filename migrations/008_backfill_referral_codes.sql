-- =============================================================
-- BACKFILL: Gen Base62 referral code từ UUID (XOR-fold approach)
-- Chạy 1 lần trên Supabase SQL Editor
-- =============================================================

-- Bước 1: Tạo function
CREATE OR REPLACE FUNCTION gen_referral_code_from_uuid(uid UUID)
RETURNS TEXT AS $$
DECLARE
    base62  TEXT  := '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
    bytes   BYTEA := uuid_send(uid);
    -- Gom 128-bit (16 bytes) thành 48-bit bằng XOR
    v_part1 BIGINT := get_byte(bytes, 0)::bigint << 40 | get_byte(bytes, 1)::bigint << 32 | get_byte(bytes, 2)::bigint << 24 | get_byte(bytes, 3)::bigint << 16 | get_byte(bytes, 4)::bigint << 8 | get_byte(bytes, 5)::bigint;
    v_part2 BIGINT := get_byte(bytes, 6)::bigint << 40 | get_byte(bytes, 7)::bigint << 32 | get_byte(bytes, 8)::bigint << 24 | get_byte(bytes, 9)::bigint << 16 | get_byte(bytes, 10)::bigint << 8 | get_byte(bytes, 11)::bigint;
    v_part3 BIGINT := get_byte(bytes, 12)::bigint << 32 | get_byte(bytes, 13)::bigint << 24 | get_byte(bytes, 14)::bigint << 16 | get_byte(bytes, 15)::bigint << 8;
    num     NUMERIC := (v_part1 # v_part2 # v_part3);
    result  TEXT    := '';
    i       INT;
BEGIN
    FOR i IN 1..8 LOOP
        result := substr(base62, (num % 62)::INT + 1, 1) || result;
        num    := floor(num / 62);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- Bước 2: Verify function trước
SELECT
    id,
    gen_referral_code_from_uuid(id) AS new_code
FROM users
LIMIT 5;


-- Bước 3: Reset TOÀN BỘ codes sang thuật toán mới
UPDATE users
SET referral_code = gen_referral_code_from_uuid(id);


-- Bước 4: Tạo UNIQUE index (phòng collision edge case)
CREATE UNIQUE INDEX IF NOT EXISTS idx_referral_code_unique ON users(referral_code);


-- Bước 5: Verify kết quả
SELECT
    count(*)                                      AS total_users,
    count(referral_code)                          AS has_code,
    count(DISTINCT referral_code)                 AS unique_codes,
    count(*) FILTER (WHERE referral_code IS NULL) AS missing_code
FROM users;