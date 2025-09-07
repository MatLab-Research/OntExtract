-- Update version_type check constraint to include 'composite'
ALTER TABLE documents DROP CONSTRAINT IF EXISTS check_version_type;
ALTER TABLE documents ADD CONSTRAINT check_version_type 
    CHECK (version_type IN ('original', 'processed', 'experimental', 'composite'));