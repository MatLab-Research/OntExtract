-- Migration: Add ExperimentDocument model for experiment-specific document processing
-- Date: 2025-01-26
-- Purpose: Enable document reuse across experiments with different embeddings/segmentation

-- Create the new experiment_documents_v2 table
CREATE TABLE IF NOT EXISTS experiment_documents_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    
    -- Processing status tracking
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Experiment-specific embedding configuration
    embedding_model VARCHAR(100),
    embedding_dimension INTEGER,
    embeddings_applied BOOLEAN NOT NULL DEFAULT 0,
    embedding_metadata TEXT, -- JSON
    
    -- Experiment-specific segmentation
    segmentation_method VARCHAR(50),
    segment_size INTEGER,
    segments_created BOOLEAN NOT NULL DEFAULT 0,
    segmentation_metadata TEXT, -- JSON
    
    -- NLP processing status
    nlp_analysis_completed BOOLEAN NOT NULL DEFAULT 0,
    nlp_tools_used TEXT, -- JSON array
    
    -- Timestamps
    processing_started_at DATETIME,
    processing_completed_at DATETIME,
    embeddings_generated_at DATETIME,
    segmentation_completed_at DATETIME,
    added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Unique constraint
    UNIQUE(experiment_id, document_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_experiment_id ON experiment_documents_v2(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_document_id ON experiment_documents_v2(document_id);
CREATE INDEX IF NOT EXISTS idx_experiment_documents_v2_status ON experiment_documents_v2(processing_status);

-- Migrate existing experiment-document relationships from the association table
INSERT OR IGNORE INTO experiment_documents_v2 (experiment_id, document_id, processing_status, added_at)
SELECT 
    experiment_id, 
    document_id, 
    'pending' as processing_status,
    COALESCE(added_at, CURRENT_TIMESTAMP) as added_at
FROM experiment_documents
WHERE experiment_id IS NOT NULL AND document_id IS NOT NULL;

-- Update trigger to maintain updated_at timestamp
CREATE TRIGGER IF NOT EXISTS trigger_experiment_documents_v2_updated_at
    AFTER UPDATE ON experiment_documents_v2
BEGIN
    UPDATE experiment_documents_v2 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;