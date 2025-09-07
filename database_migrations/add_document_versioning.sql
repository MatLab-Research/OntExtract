-- Add document versioning support to enable unified processing interface
-- This migration extends the existing parent_document_id functionality to support proper versioning

-- Add versioning fields to documents table
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_type VARCHAR(20) DEFAULT 'original';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS experiment_id INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_document_id INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS processing_notes TEXT;

-- Add foreign key constraints
ALTER TABLE documents ADD CONSTRAINT fk_documents_experiment 
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL;
    
ALTER TABLE documents ADD CONSTRAINT fk_documents_source 
    FOREIGN KEY (source_document_id) REFERENCES documents(id) ON DELETE CASCADE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_version_number ON documents(version_number);
CREATE INDEX IF NOT EXISTS idx_documents_version_type ON documents(version_type);  
CREATE INDEX IF NOT EXISTS idx_documents_experiment_id ON documents(experiment_id);
CREATE INDEX IF NOT EXISTS idx_documents_source_document_id ON documents(source_document_id);

-- Create a view to easily find document version chains
CREATE OR REPLACE VIEW document_version_chains AS
SELECT 
    COALESCE(d.source_document_id, d.id) as root_document_id,
    d.id as document_id,
    d.title,
    d.version_number,
    d.version_type,
    d.experiment_id,
    d.created_at,
    d.status,
    e.name as experiment_name
FROM documents d
LEFT JOIN experiments e ON d.experiment_id = e.id
ORDER BY COALESCE(d.source_document_id, d.id), d.version_number;

-- Update existing documents to have proper version information
-- All existing documents become version 1 originals
UPDATE documents 
SET version_number = 1, version_type = 'original' 
WHERE version_number IS NULL OR version_type IS NULL;

-- For documents that use parent_document_id for OED grouping (keep that functionality)
-- We'll distinguish between OED parent relationships and versioning relationships
-- OED documents will keep using parent_document_id, versions will use source_document_id

-- Add check constraints for version types
ALTER TABLE documents ADD CONSTRAINT check_version_type 
    CHECK (version_type IN ('original', 'processed', 'experimental'));
    
-- Add check constraint for version numbers (must be positive)
ALTER TABLE documents ADD CONSTRAINT check_version_number_positive 
    CHECK (version_number > 0);

-- Comments for documentation
COMMENT ON COLUMN documents.version_number IS 'Sequential version number within a document family';
COMMENT ON COLUMN documents.version_type IS 'Type of version: original, processed, experimental';
COMMENT ON COLUMN documents.experiment_id IS 'Associated experiment (for experimental versions)';
COMMENT ON COLUMN documents.source_document_id IS 'Original document this version derives from';
COMMENT ON COLUMN documents.processing_notes IS 'Notes about processing operations that created this version';