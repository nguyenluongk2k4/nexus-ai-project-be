# ✅ Referral Code V2 - Deployment Checklist

## Pre-Deployment

### Code Review
- [x] Algorithm implemented in Python (`_uuid_to_base62()`)
- [x] Register endpoint updated (email/password)
- [x] Google OAuth endpoint updated
- [x] SQL migration created with backfill logic
- [x] Test suite created and passing
- [x] Documentation complete

### Local Testing
- [ ] Run test suite: `python tests/test_referral_code_v2.py`
- [ ] Expected: `✅ ALL TESTS PASSED`
- [ ] Test registration endpoint locally
- [ ] Verify code format: 16 chars, XXXXXXXX + YYYYYYYY
- [ ] Test multiple registrations (verify different codes)

### Database
- [ ] Backup existing database (production only)
- [ ] Review migration: `migrations/009_new_referral_code_algorithm.sql`
- [ ] Run migration on development DB
- [ ] Verify migration results (see queries below)
- [ ] Check UNIQUE index is active: `idx_referral_code_unique`

---

## Migration Verification Queries

After running migration, execute these SQL queries:

### Query 1: Basic Stats
```sql
SELECT 
    COUNT(*) as total_users,
    COUNT(referral_code) as with_code,
    COUNT(DISTINCT referral_code) as unique_codes,
    COUNT(*) FILTER (WHERE referral_code IS NULL) as missing_code
FROM users;

-- Expected:
-- total_users: 1234 (your count)
-- with_code: 1234 (all have codes)
-- unique_codes: 1234 (all unique)
-- missing_code: 0 (none NULL)
```

### Query 2: Code Format Check
```sql
SELECT 
    MIN(LENGTH(referral_code)) as min_length,
    MAX(LENGTH(referral_code)) as max_length,
    COUNT(*) FILTER (WHERE LENGTH(referral_code) != 16) as wrong_length
FROM users
WHERE referral_code IS NOT NULL;

-- Expected:
-- min_length: 16 (if old codes still exist, may be higher)
-- max_length: 16 (all new codes are 16)
-- wrong_length: 0 (or count of old codes if keeping)
```

### Query 3: Sample New Codes
```sql
SELECT id, referral_code, LENGTH(referral_code) as len, created_at 
FROM users 
WHERE LENGTH(referral_code) = 16
ORDER BY created_at DESC
LIMIT 10;

-- Expected:
-- Format: XXXXXXXX + YYYYYYYY (e.g., 0859cc4dbjFxdAwK)
-- Length: 16
-- All unique
```

### Query 4: Index Status
```sql
SELECT * FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname LIKE '%referral%';

-- Expected:
-- idx_referral_code_unique exists and is unique
-- idx_users_referral_code exists
```

---

## Deployment Steps

### Step 1: Deploy Backend Code
- [ ] Merge & deploy backend changes (routes.py, repository.py)
- [ ] Verify backend starts without errors
- [ ] Check logs for any import errors

### Step 2: Run Migration
- [ ] SSH to production DB server
- [ ] Run migration: `psql < migrations/009_new_referral_code_algorithm.sql`
- [ ] Wait for completion (backfill may take time if many users)
- [ ] Perform verification queries (above)

### Step 3: Smoke Tests
- [ ] Create new user via email: Check referral_code is 16 chars
- [ ] Create new user via Google: Check referral_code is 16 chars
- [ ] Test referral code lookup: Works with new codes
- [ ] Test existing referrals: Still work with old codes

### Step 4: Monitor
- [ ] Watch application logs for errors
- [ ] Monitor database for any locks/issues
- [ ] Check referral metrics (code generation rate)
- [ ] Verify no duplicate code errors

---

## Rollback Steps (If Something Goes Wrong)

### Option 1: Revert to Old Algorithm
```sql
-- Only revert new codes (16 chars)
UPDATE users 
SET referral_code = uuid_to_base62(users.id)
WHERE LENGTH(referral_code) = 16;
```

### Option 2: Full Rollback
```bash
# 1. Revert backend code changes
git revert <commit_hash>

# 2. Restore database from backup
pg_restore -d nexusai backup_file.sql

# 3. Restart services
systemctl restart nexusai-api
```

---

## Success Criteria

**Deployment is successful when:**
- [x] All existing referrals still work
- [x] New users get 16-char codes
- [x] Email registration works
- [x] Google OAuth registration works
- [x] Referral lookup/validation works
- [x] No duplicate key errors
- [x] No NULL referral_code in new users
- [x] Performance is unchanged or improved

---

## Post-Deployment

### Monitoring (First 24 hours)
- [ ] Check error logs every 4 hours
- [ ] Monitor new user registration rate
- [ ] Verify referral redemption still works
- [ ] Check database performance metrics

### Long-term
- [ ] Add alert: If new user created without referral_code
- [ ] Add alert: If duplicate referral_code generated
- [ ] Log: Sample of generated codes for audit
- [ ] Review: Migration impact on DB size/performance

---

## Document Locations

- **Algorithm Details**: [REFERRAL_CODE_MIGRATION_GUIDE.md](REFERRAL_CODE_MIGRATION_GUIDE.md)
- **Test Suite**: [tests/test_referral_code_v2.py](tests/test_referral_code_v2.py)
- **Migration File**: [migrations/009_new_referral_code_algorithm.sql](migrations/009_new_referral_code_algorithm.sql)
- **Code Changes**: 
  - [modules/referral/infrastructure/repository.py](modules/referral/infrastructure/repository.py)
  - [modules/auth/api/routes.py](modules/auth/api/routes.py)

---

## Timeline Estimate

| Task | Duration | Owner |
|------|----------|-------|
| Local testing | 15 min | Dev |
| Migration (dev) | 5 min | Dev |
| Code review | 30 min | Lead |
| Production deploy | 10 min | DevOps |
| Migration (prod) | 5-10 min | DBA |
| Smoke tests | 15 min | QA |
| Monitoring | 24 hours | Ops |

**Total: ~1.5 hours deployment window**

---

## Emergency Contacts

- Database: [DBA contact]
- Backend: [Backend lead]
- Ops: [Operations team]

---

**Last Updated**: Feb 23, 2026
**Algorithm Version**: V2
**Status**: 🟢 READY TO DEPLOY
