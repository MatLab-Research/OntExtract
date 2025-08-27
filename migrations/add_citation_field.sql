-- Migration: Add source_citation field to term_versions table
-- Date: August 24, 2025
-- Purpose: PROV-O compliance and citation tracking for term versions

BEGIN;

-- Add the source_citation column to term_versions table
ALTER TABLE term_versions 
ADD COLUMN source_citation TEXT;

-- Add index for performance on citation queries (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_term_versions_source_citation 
ON term_versions(source_citation) 
WHERE source_citation IS NOT NULL;

-- Commit the transaction
COMMIT;

-- Verification query (run separately to confirm)
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'term_versions' AND column_name = 'source_citation';
