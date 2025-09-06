-- Enhance experiment_documents table to store experiment-specific processing data
-- This separates processing metadata per experiment-document pair

-- Add processing-related columns
ALTER TABLE experiment_documents ADD COLUMN processing_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE experiment_documents ADD COLUMN processing_metadata JSON;
ALTER TABLE experiment_documents ADD COLUMN embeddings_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE experiment_documents ADD COLUMN embeddings_metadata JSON;
ALTER TABLE experiment_documents ADD COLUMN segments_created BOOLEAN DEFAULT FALSE;
ALTER TABLE experiment_documents ADD COLUMN segments_metadata JSON;
ALTER TABLE experiment_documents ADD COLUMN nlp_analysis_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE experiment_documents ADD COLUMN nlp_results JSON;
ALTER TABLE experiment_documents ADD COLUMN processed_at TIMESTAMP;
ALTER TABLE experiment_documents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add comments
COMMENT ON COLUMN experiment_documents.processing_status IS 'Status: pending, processing, completed, error';
COMMENT ON COLUMN experiment_documents.processing_metadata IS 'General experiment-specific processing metadata';
COMMENT ON COLUMN experiment_documents.embeddings_applied IS 'Whether embeddings have been generated for this experiment';
COMMENT ON COLUMN experiment_documents.embeddings_metadata IS 'Embedding model info and metrics for this experiment';
COMMENT ON COLUMN experiment_documents.segments_created IS 'Whether document has been segmented for this experiment';
COMMENT ON COLUMN experiment_documents.segments_metadata IS 'Segmentation parameters and results';
COMMENT ON COLUMN experiment_documents.nlp_analysis_completed IS 'Whether NLP analysis is complete for this experiment';
COMMENT ON COLUMN experiment_documents.nlp_results IS 'Experiment-specific NLP analysis results';

-- Add index for efficient querying by status
CREATE INDEX idx_experiment_documents_status ON experiment_documents(processing_status);
CREATE INDEX idx_experiment_documents_updated ON experiment_documents(updated_at);