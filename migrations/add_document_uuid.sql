-- Add UUID column to documents table for clean URLs
-- Keeps integer ID as primary key for foreign key relationships

-- Add uuid column with default value generator
ALTER TABLE documents 
ADD COLUMN uuid UUID DEFAULT gen_random_uuid() NOT NULL;

-- Generate UUIDs for existing documents
UPDATE documents SET uuid = gen_random_uuid() WHERE uuid IS NULL;

-- Add unique constraint on uuid
ALTER TABLE documents 
ADD CONSTRAINT documents_uuid_unique UNIQUE (uuid);

-- Add index for fast uuid lookups
CREATE INDEX idx_documents_uuid ON documents(uuid);
