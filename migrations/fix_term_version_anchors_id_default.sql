-- Migration: Fix term_version_anchors id column default
-- Date: August 24, 2025
-- Purpose: Add UUID default to fix null constraint violation when inserting anchors

BEGIN;

-- Add the missing UUID default for the id column
ALTER TABLE term_version_anchors 
ALTER COLUMN id SET DEFAULT gen_random_uuid();

COMMIT;

-- Verification: Check that default is set
-- SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'term_version_anchors' AND column_name = 'id';
