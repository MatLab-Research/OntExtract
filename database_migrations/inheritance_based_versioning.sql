-- Migration: Inheritance-Based Versioning System
-- Replaces composite document approach with version inheritance
-- Each document version inherits all processing from previous versions

BEGIN;

-- Add version changelog to track what changed in each version
CREATE TABLE IF NOT EXISTS version_changelog (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    change_type VARCHAR(50) NOT NULL, -- 'embeddings_added', 'segments_added', 'content_updated'
    change_description TEXT,
    previous_version INTEGER, -- version this inherits from
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id),
    processing_metadata JSONB,
    
    CONSTRAINT unique_document_version_change UNIQUE(document_id, version_number, change_type)
);

-- Index for efficient version queries
CREATE INDEX idx_version_changelog_document_version ON version_changelog(document_id, version_number);
CREATE INDEX idx_version_changelog_change_type ON version_changelog(change_type);

-- Function to inherit processing data from previous version
-- This will copy embeddings and segments from previous version when creating new version
CREATE OR REPLACE FUNCTION inherit_processing_data(
    source_document_id INTEGER,
    target_document_id INTEGER
) RETURNS VOID AS $$
BEGIN
    -- Copy embeddings from source to target
    INSERT INTO document_embeddings (
        document_id, term, period, embedding, 
        model_name, context_window, extraction_method, metadata, created_at
    )
    SELECT 
        target_document_id, term, period, embedding,
        model_name, context_window, extraction_method, metadata, CURRENT_TIMESTAMP
    FROM document_embeddings 
    WHERE document_id = source_document_id;

    -- Copy text segments from source to target  
    INSERT INTO text_segments (
        document_id, content, segment_type, segment_number,
        start_position, end_position, parent_segment_id, level,
        word_count, character_count, sentence_count, language, language_confidence,
        embedding, embedding_model, processed, processing_notes, topics, keywords,
        sentiment_score, complexity_score, created_at
    )
    SELECT 
        target_document_id, content, segment_type, segment_number,
        start_position, end_position, parent_segment_id, level,
        word_count, character_count, sentence_count, language, language_confidence,
        embedding, embedding_model, processed, processing_notes, topics, keywords,
        sentiment_score, complexity_score, CURRENT_TIMESTAMP
    FROM text_segments
    WHERE document_id = source_document_id;
    
    -- Copy processing summary if exists
    INSERT INTO document_processing_summary (
        document_id, processing_type, processing_method, result_summary,
        processing_timestamp, metadata, source_document_id
    )
    SELECT 
        target_document_id, processing_type, processing_method, result_summary,
        CURRENT_TIMESTAMP, metadata, target_document_id
    FROM document_processing_summary
    WHERE document_id = source_document_id;

END;
$$ LANGUAGE plpgsql;

-- Add helper function to get latest version of a document
CREATE OR REPLACE FUNCTION get_latest_document_version(base_document_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    latest_version INTEGER;
BEGIN
    -- Find the highest version number for documents with same base ID
    SELECT MAX(d.version_number) INTO latest_version
    FROM documents d 
    WHERE (d.id = base_document_id OR d.source_document_id = base_document_id)
    OR (d.source_document_id IN (
        SELECT source_document_id FROM documents WHERE id = base_document_id
    ));
    
    RETURN COALESCE(latest_version, 1);
END;
$$ LANGUAGE plpgsql;

-- Add helper function to get document ID for specific version
CREATE OR REPLACE FUNCTION get_document_version_id(base_document_id INTEGER, target_version INTEGER)
RETURNS INTEGER AS $$
DECLARE
    version_document_id INTEGER;
BEGIN
    -- Find document ID for specific version
    SELECT d.id INTO version_document_id
    FROM documents d 
    WHERE ((d.id = base_document_id AND d.version_number = target_version)
        OR (d.source_document_id = base_document_id AND d.version_number = target_version))
    LIMIT 1;
    
    RETURN version_document_id;
END;
$$ LANGUAGE plpgsql;

-- Note: ALTER TABLE operations should be run separately as superuser if needed
-- For now, we'll work with existing schema and add the column later

-- View for getting complete version history of a document
CREATE OR REPLACE VIEW document_version_history AS
SELECT 
    d.id,
    d.title,
    d.version_number,
    d.version_type,
    d.created_at as version_created,
    d.source_document_id,
    COALESCE(d.source_document_id, d.id) as base_document_id,
    (d.version_number = 1 AND d.version_type = 'original') as is_base_document,
    -- Processing counts for this specific version
    COALESCE(e.embedding_count, 0) as embedding_count,
    COALESCE(s.segment_count, 0) as segment_count,
    -- Version changelog info
    array_agg(DISTINCT vc.change_type) FILTER (WHERE vc.change_type IS NOT NULL) as changes_in_version,
    vc.change_description
FROM documents d
LEFT JOIN (
    SELECT document_id, COUNT(*) as embedding_count 
    FROM document_embeddings 
    GROUP BY document_id
) e ON d.id = e.document_id
LEFT JOIN (
    SELECT document_id, COUNT(*) as segment_count 
    FROM text_segments 
    GROUP BY document_id  
) s ON d.id = s.document_id
LEFT JOIN version_changelog vc ON d.id = vc.document_id AND d.version_number = vc.version_number
GROUP BY d.id, d.title, d.version_number, d.version_type, d.created_at, 
         d.source_document_id, e.embedding_count, 
         s.segment_count, vc.change_description
ORDER BY COALESCE(d.source_document_id, d.id), d.version_number;

COMMIT;