-- Migration: Add ExperimentDocument model for experiment-specific document processing
-- Date: 2025-01-26
-- Purpose: Enable document reuse across experiments with different embeddings/segmentation
-- Database: PostgreSQL

-- Create the new experiment_documents_v2 table
CREATE TABLE IF NOT EXISTS experiment_documents_v2 (
    id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    
    -- Processing status tracking
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Experiment-specific embedding configuration
    embedding_model VARCHAR(100),
    embedding_dimension INTEGER,
    embeddings_applied BOOLEAN NOT NULL DEFAULT FALSE,
    embedding_metadata TEXT,
    
    -- Experiment-specific segmentation
    segmentation_method VARCHAR(50),
    segment_size INTEGER,
    segments_created BOOLEAN NOT NULL DEFAULT FALSE,
    segmentation_metadata TEXT,
    
    -- NLP processing status
    nlp_analysis_completed BOOLEAN NOT NULL DEFAULT FALSE,
    nlp_tools_used TEXT,
    
    -- Timestamps
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    embeddings_generated_at TIMESTAMP,
    segmentation_completed_at TIMESTAMP,
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    CONSTRAINT fk_exp_doc_experiment FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE,
    CONSTRAINT fk_exp_doc_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Unique constraint
    CONSTRAINT unique_exp_doc UNIQUE(experiment_id, document_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_experiment_id ON experiment_documents_v2(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_document_id ON experiment_documents_v2(document_id);
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_status ON experiment_documents_v2(processing_status);

-- Migrate existing experiment-document relationships from the association table
INSERT INTO experiment_documents_v2 (experiment_id, document_id, processing_status, added_at)
SELECT 
    experiment_id, 
    document_id, 
    'pending' as processing_status,
    COALESCE(added_at, CURRENT_TIMESTAMP) as added_at
FROM experiment_documents
WHERE experiment_id IS NOT NULL 
  AND document_id IS NOT NULL
ON CONFLICT (experiment_id, document_id) DO NOTHING;

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_experiment_documents_v2_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_experiment_documents_v2_updated_at ON experiment_documents_v2;
CREATE TRIGGER trigger_experiment_documents_v2_updated_at
    BEFORE UPDATE ON experiment_documents_v2
    FOR EACH ROW
    EXECUTE FUNCTION update_experiment_documents_v2_updated_at();