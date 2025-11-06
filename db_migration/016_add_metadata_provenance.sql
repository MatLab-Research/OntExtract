-- Migration: Add metadata provenance tracking to documents
-- Date: 2025-01-06
-- Description: Adds metadata_provenance JSONB field to track the source and confidence of each metadata field

-- Add metadata_provenance column to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS metadata_provenance JSONB DEFAULT '{}';

COMMENT ON COLUMN documents.metadata_provenance IS 'Tracks provenance for each metadata field. Structure: {field_name: {source: str, confidence: float, timestamp: str, raw_value: any}}';

-- Create index on metadata_provenance for faster queries
CREATE INDEX IF NOT EXISTS idx_documents_metadata_provenance
ON documents USING gin(metadata_provenance);

-- Example metadata_provenance structure:
-- {
--   "title": {
--     "source": "crossref",  -- 'user', 'crossref', 'file_analysis', 'llm'
--     "confidence": 0.95,
--     "timestamp": "2025-01-06T10:30:00Z",
--     "raw_value": "Original Title from CrossRef"
--   },
--   "authors": {
--     "source": "user",
--     "confidence": 1.0,
--     "timestamp": "2025-01-06T10:32:00Z",
--     "raw_value": ["Author 1", "Author 2"]
--   },
--   "publication_year": {
--     "source": "crossref",
--     "confidence": 1.0,
--     "timestamp": "2025-01-06T10:30:00Z",
--     "raw_value": 2020
--   }
-- }
