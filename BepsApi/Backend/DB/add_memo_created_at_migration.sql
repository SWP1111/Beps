-- Migration script to add created_at column to memo_data table
-- This script adds the created_at column and sets it to the current modified_at value for existing records

-- Add the created_at column with default value
ALTER TABLE memo_data 
ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Update existing records to use modified_at as initial created_at value
-- This preserves the original registration date for existing memos
UPDATE memo_data 
SET created_at = modified_at 
WHERE created_at IS NULL;

-- Make the column NOT NULL after setting values
ALTER TABLE memo_data 
ALTER COLUMN created_at SET NOT NULL;

-- Add comment to document the purpose
COMMENT ON COLUMN memo_data.created_at IS 'Registration date (등록일) - never changes after memo creation';
COMMENT ON COLUMN memo_data.modified_at IS 'Last modification date - updates when memo is edited or status changed';

-- Verify the migration
SELECT 
    id,
    created_at,
    modified_at,
    title,
    status
FROM memo_data
ORDER BY id DESC
LIMIT 10;
