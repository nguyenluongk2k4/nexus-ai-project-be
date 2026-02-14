-- Migration: Create chat_events table for event logging (PostgreSQL)
-- Date: 2026-02-12
-- Description: Create table to track chat processing events (intent_detected, render_started, render_completed, error)

CREATE TABLE IF NOT EXISTS chat_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE chat_events IS 'Track events during chat session processing (intent detection, rendering, errors)';

-- Show table structure (portable SQL)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'chat_events'
ORDER BY ordinal_position;
