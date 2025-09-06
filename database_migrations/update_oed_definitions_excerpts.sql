-- Migration: Update OED definitions to store excerpts and links instead of full text
-- Date: 2025-09-06
-- Purpose: Reduce OED data storage to respect licensing and improve performance

-- Add new columns for excerpts and OED links
ALTER TABLE oed_definitions 
ADD COLUMN definition_excerpt VARCHAR(300),
ADD COLUMN oed_sense_id VARCHAR(100),
ADD COLUMN oed_url VARCHAR(500);

-- Migrate existing data to use excerpts
UPDATE oed_definitions 
SET definition_excerpt = CASE 
    WHEN LENGTH(definition_text) > 300 THEN LEFT(definition_text, 297) || '...'
    ELSE definition_text
END
WHERE definition_excerpt IS NULL;

-- Generate OED URLs for existing entries (basic format)
UPDATE oed_definitions 
SET oed_url = 'https://www.oed.com/dictionary/' || 
    (SELECT LOWER(term_text) FROM terms WHERE terms.id = oed_definitions.term_id) ||
    '_n1#' || COALESCE(definition_number, '1')
WHERE oed_url IS NULL;

-- Set oed_sense_id for existing entries
UPDATE oed_definitions 
SET oed_sense_id = COALESCE(definition_number, '1')
WHERE oed_sense_id IS NULL;

-- Drop the old full text column after migration (optional - comment out if you want to keep backup)
-- ALTER TABLE oed_definitions DROP COLUMN definition_text;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_oed_definitions_sense_id ON oed_definitions(oed_sense_id);
CREATE INDEX IF NOT EXISTS idx_oed_definitions_excerpt ON oed_definitions(definition_excerpt);

-- Update any views or procedures that reference definition_text (if any exist)
-- Note: Check app code for any remaining references to definition_text

COMMIT;