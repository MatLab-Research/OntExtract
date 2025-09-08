-- Migration: Add segmentation method tracking to text_segments
-- This allows documents to have multiple sets of segments created by different methods

BEGIN;

-- Add segmentation_method column to track how segments were created
ALTER TABLE text_segments 
ADD COLUMN segmentation_method VARCHAR(50) DEFAULT 'manual';

-- Add segmentation_job_id to link back to the processing job that created these segments
ALTER TABLE text_segments 
ADD COLUMN segmentation_job_id INTEGER REFERENCES processing_jobs(id) ON DELETE SET NULL;

-- Update existing segments to have default method
UPDATE text_segments 
SET segmentation_method = 'paragraph' 
WHERE segment_type = 'paragraph' AND segmentation_method = 'manual';

-- Add indexes for efficient querying by method
CREATE INDEX IF NOT EXISTS idx_text_segments_segmentation_method ON text_segments(segmentation_method);
CREATE INDEX IF NOT EXISTS idx_text_segments_doc_method ON text_segments(document_id, segmentation_method);
CREATE INDEX IF NOT EXISTS idx_text_segments_job_id ON text_segments(segmentation_job_id);

COMMIT;