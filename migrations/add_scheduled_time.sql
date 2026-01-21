-- Add scheduled_time column to timeline_items table
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/.../editor

ALTER TABLE timeline_items 
ADD COLUMN IF NOT EXISTS scheduled_time VARCHAR(5);

-- Set default time (8:00 AM) for existing rows  
UPDATE timeline_items 
SET scheduled_time = '08:00' 
WHERE scheduled_time IS NULL;

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'timeline_items';
