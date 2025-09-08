-- Migration: Add document_embeddings table with proper vector type
-- This table stores embeddings for documents with period-aware processing

BEGIN;

-- Create the document_embeddings table with vector type
CREATE TABLE IF NOT EXISTS public.document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    term VARCHAR(200) NOT NULL,
    period INTEGER,
    embedding vector(384),
    model_name VARCHAR(100),
    context_window TEXT,
    extraction_method VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_term ON document_embeddings(term);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_period ON document_embeddings(period);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_model ON document_embeddings(model_name);

-- Create vector similarity search index (using ivfflat)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Add permissions
ALTER TABLE public.document_embeddings OWNER TO ontextract_user;

COMMIT;