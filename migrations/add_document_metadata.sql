-- Add processing_metadata column to documents table for processing information
-- This includes embeddings status, processing info, and other metadata

-- Add processing_metadata column to documents table (renamed to avoid SQLAlchemy conflict)
ALTER TABLE documents ADD COLUMN processing_metadata JSON;

-- Add comment to document the column purpose
COMMENT ON COLUMN documents.processing_metadata IS 'General metadata for processing info, embeddings, and document analysis';