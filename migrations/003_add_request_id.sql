-- Migration: Add request_id column for request tracking (PostgreSQL)
-- Date: 2026-02-12
-- Description: Add request_id column to track async requests from frontend

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS request_id UUID UNIQUE;

-- Add comment for documentation
COMMENT ON COLUMN chat_sessions.request_id IS 'UUID to track async request - correlate FE request with BE processing';

-- Verify changes
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'chat_sessions'
AND column_name IN ('request_id', 'status');
