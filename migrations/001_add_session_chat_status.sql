-- Migration: Add status column to chat_sessions table (PostgreSQL)
-- Date: 2026-02-12
-- Description: Add status column to track chat_sessions processing state (idle, rendering)

-- Add status column with default value
ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'idle';

-- Add comment for documentation
COMMENT ON COLUMN chat_sessions.status IS 'Status of chat session: idle (ready for input), rendering (processing tree/intent)';

-- Verify changes
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'chat_sessions'
AND column_name = 'status';
