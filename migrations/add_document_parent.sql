-- Migration: add parent_document_id to documents for hierarchical references (e.g., per-sense OED entries)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS parent_document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent_document_id);
