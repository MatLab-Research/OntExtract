-- Add composite document support to enable unified processing interface
-- This migration extends the existing versioning to support composite aggregation

-- Add composite document type to existing version_type constraint
ALTER TABLE documents DROP CONSTRAINT IF EXISTS check_version_type;
ALTER TABLE documents ADD CONSTRAINT check_version_type 
    CHECK (version_type IN ('original', 'processed', 'experimental', 'composite'));

-- Add composite-specific fields
ALTER TABLE documents ADD COLUMN IF NOT EXISTS composite_strategy VARCHAR(30); 
-- Strategies: 'all_processing', 'latest_version', 'selective'

-- Create composite sources junction table
CREATE TABLE IF NOT EXISTS composite_sources (
    id SERIAL PRIMARY KEY,
    composite_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    processing_priority INTEGER DEFAULT 1, -- Higher priority = preferred source for conflicting processing
    included_processing_types TEXT[], -- JSON array of processing types to include from this source
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(composite_document_id, source_document_id)
);

CREATE INDEX IF NOT EXISTS idx_composite_sources_composite ON composite_sources(composite_document_id);
CREATE INDEX IF NOT EXISTS idx_composite_sources_source ON composite_sources(source_document_id);

-- Create processing aggregation table for efficient queries
CREATE TABLE IF NOT EXISTS document_processing_summary (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    processing_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'available', 'processing', 'failed'
    source_document_id INTEGER REFERENCES documents(id), -- Which document provided this processing
    job_id INTEGER REFERENCES processing_jobs(id), -- Link to the actual job
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, processing_type, source_document_id)
);

CREATE INDEX IF NOT EXISTS idx_processing_summary_document ON document_processing_summary(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_summary_type ON document_processing_summary(processing_type);

-- Create view for easy composite document querying
CREATE OR REPLACE VIEW document_processing_availability AS
SELECT 
    d.id as document_id,
    d.title,
    d.version_type,
    d.composite_strategy,
    ARRAY_AGG(DISTINCT dps.processing_type) FILTER (WHERE dps.processing_type IS NOT NULL) as available_processing,
    COUNT(DISTINCT cs.source_document_id) as source_count,
    MAX(dps.updated_at) as last_processing_update
FROM documents d
LEFT JOIN document_processing_summary dps ON d.id = dps.document_id AND dps.status = 'available'
LEFT JOIN composite_sources cs ON d.id = cs.composite_document_id
WHERE d.version_type IN ('original', 'composite')
GROUP BY d.id, d.title, d.version_type, d.composite_strategy;

-- Comments for documentation
COMMENT ON COLUMN documents.composite_strategy IS 'Strategy for composite documents: all_processing, latest_version, selective';
COMMENT ON TABLE composite_sources IS 'Links composite documents to their constituent source documents';
COMMENT ON TABLE document_processing_summary IS 'Efficient summary of processing capabilities available per document';