-- This SQL script runs during PostgreSQL initialization (first startup only)
-- It enables the pgvector extension for the ontextract_db database

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
