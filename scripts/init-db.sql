-- OntExtract Database Initialization Script
-- This script runs when the PostgreSQL container is first created

-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create additional extensions that might be useful for text processing
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Set up database configuration
ALTER DATABASE ontextract_db SET timezone TO 'UTC';

-- Create indexes for better performance (will be created by SQLAlchemy models, but good to have)
-- Note: These will be created by the application models, this is just a placeholder
-- for any custom database setup we might need in the future

-- Log the initialization
DO $$
BEGIN
    RAISE NOTICE 'OntExtract database initialized with vector extension and additional utilities';
END
$$;
