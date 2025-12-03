#!/bin/bash
set -e

# This script runs during PostgreSQL initialization (first startup only)
# It enables the pgvector extension for the ontextract_db database

echo "Enabling pgvector extension for ontextract_db..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create pgvector extension
    CREATE EXTENSION IF NOT EXISTS vector;

    -- Verify extension is installed
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOSQL

echo "pgvector extension enabled successfully!"
