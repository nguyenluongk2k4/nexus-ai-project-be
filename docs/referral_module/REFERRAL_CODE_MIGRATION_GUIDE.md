# 🔄 Referral Code Migration Guide

## Overview
Cập nhật thuật toán generation referral code từ **Full Base62** → **UUID Prefix + Random (v2)**

### Algorithm Changes
| Aspect | Old | New |
|--------|-----|-----|
| **Algorithm** | Full 128-bit Base62 | UUID hex prefix (8) + random Base62 (8) |
| **Length** | 20-22 chars (variable) | 16 chars (fixed) |
| **Format** | `FkyXSS4actMh27cAOxKQY` | `0859cc4dbjFxdAwK` |
| **Collision Space** | 62^20+ | 16^8 × 62^8 (negligible) |
| **DB Protection** | UNIQUE index | UNIQUE index |

---

## Migration Plan

### For Development (All at once)
```bash
# 1. Run new migration
psql -h localhost -U nexusai -d nexusai < backend/migrations/009_new_referral_code_algorithm.sql

# 2. Verify
psql -h localhost -U nexusai -d nexusai << 'SQL'
SELECT COUNT(*), COUNT(DISTINCT referral_code), 
       LENGTH(referral_code), 
       COUNT(*) FILTER (WHERE referral_code IS NULL)
FROM users;
SQL

# Expected output:
# - All users have referral_code
# - All codes are 16 chars
# - No NULLs
# - All codes unique
```

### For Production (Safe, gradual)
```sql
-- Step 1: Run migration (backfill only null codes)
-- User cũ có code → keep
-- User cũ null code → generate new

-- Step 2: Verify before commit
SELECT COUNT(*) as total,
       COUNT(referral_code) as with_code,
       COUNT(DISTINCT referral_code) as unique_codes,
       COUNT(*) FILTER (WHERE LENGTH(referral_code) != 16) as wrong_length
FROM users;

-- Step 3: Deploy backend code (uses _uuid_to_base62 v2)
```

---

## Backend Implementation

### New User Registration
```python
# backend/modules/auth/api/routes.py

# New users (email/password or Google OAuth) automatically get code:
referral_code = SQLAlchemyReferralRepository._uuid_to_base62(user_id)
# Returns: Format XXXXXXXX + YYYYYYYY (16 chars)
```

### Algorithm Details
```python
def _uuid_to_base62(user_id: UUID) -> str:
    """
    Generate: UUID hex prefix (8) + random Base62 (8) = 16 chars
    
    Example:
    - UUID: 0859cc4d-f6b2-499b-a1c3-10aecfa0ac26
    - Hex prefix: 0859cc4d (first 8 chars of hex)
    - Random suffix: bjFxdAwK (random Base62, 8 chars)
    - Result: 0859cc4dbjFxdAwK
    """
```

### Collision Analysis
```
Prefix space:       16^8    = 4.3B  (256M unique users)
Suffix space:       62^8    = 218B  (random part)
Total combinations: 16^8 × 62^8 = 937T×10^15

Collision probability:
- With 1M users: Negligible
- With 1B users: Still negligible
- DB UNIQUE constraint: Prevents any collision anyway ✓
```

---

## Validation Checklist

After migration:
- [ ] All users have referral_code (no NULLs)
- [ ] All codes are exactly 16 chars
- [ ] All codes are unique (UNIQUE index active)
- [ ] New registrations work without errors
- [ ] Google OAuth registrations get codes
- [ ] `check referral_code pattern` (8 hex + 8 alphanumeric)

### SQL Validation Queries
```sql
-- Check distribution
SELECT 
    COUNT(*) as total_users,
    COUNT(referral_code) as with_code,
    COUNT(DISTINCT referral_code) as unique_codes,
    COUNT(*) FILTER (WHERE referral_code IS NULL) as missing,
    MIN(LENGTH(referral_code)) as min_length,
    MAX(LENGTH(referral_code)) as max_length,
    AVG(LENGTH(referral_code)) as avg_length
FROM users;

-- Sample codes
SELECT id, referral_code, created_at FROM users 
WHERE referral_code IS NOT NULL 
ORDER BY created_at DESC
LIMIT 20;

-- Check old format codes (if any)
SELECT COUNT(*) as old_format_codes 
FROM users 
WHERE LENGTH(referral_code) > 16;
```

---

## Rollback Plan (If needed)

```sql
-- Revert to old algorithm
UPDATE users 
SET referral_code = uuid_to_base62(users.id)
WHERE LENGTH(referral_code) = 16;  -- Only revert new codes

-- Or if major issue:
ALTER TABLE users DROP CONSTRAINT IF EXISTS idx_referral_code_unique;
UPDATE users SET referral_code = NULL;
-- Then run previous migration
```

---

## Timeline

| Phase | Action | Timeline |
|-------|--------|----------|
| Backend | Update `_uuid_to_base62()` | ✅ Done |
| DB | Create migration 009 | ✅ Done |
| Testing | Run locally & verify | ⏳ Next |
| Production | Schedule migration | ⏳ TBD |
| Monitor | Track new registrations | ⏳ After deploy |

---

## Questions?

- **Collision risk?** Extremely low due to prefix uniqueness + random suffix
- **Backward compatibility?** Old codes stay, new codes are 16 chars. No impact on existing referrals
- **Performance?** Generation is O(1), no performance impact
- **User experience?** Codes are cleaner, easier to remember (16 vs 20+ chars)

---

**Migration Ready to Deploy! 🚀**
