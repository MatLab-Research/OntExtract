-- Add support for reference documents
-- Add document_type field to distinguish between documents and references
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR(20) DEFAULT 'document';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_metadata JSON;

-- Create experiment_references table for linking references to experiments
CREATE TABLE IF NOT EXISTS experiment_references (
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    reference_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    include_in_analysis BOOLEAN DEFAULT false,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (experiment_id, reference_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_experiment_references_experiment ON experiment_references(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_references_reference ON experiment_references(reference_id);

-- Update existing documents to have the correct type
UPDATE documents SET document_type = 'document' WHERE document_type IS NULL;
