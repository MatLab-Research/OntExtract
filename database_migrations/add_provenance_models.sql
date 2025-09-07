-- Add PROV-O compliant provenance tracking tables
-- This migration creates first-class database entities for PROV-O compliance

-- Create provenance_entities table
CREATE TABLE IF NOT EXISTS provenance_entities (
    id SERIAL PRIMARY KEY,
    
    -- PROV-O Core Properties
    prov_id VARCHAR(255) UNIQUE NOT NULL,
    prov_type VARCHAR(100) NOT NULL,
    prov_label VARCHAR(500),
    generated_at_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invalidated_at_time TIMESTAMP,
    
    -- Attribution and Agency
    attributed_to_agent VARCHAR(255),
    
    -- Derivation relationships
    derived_from_entity VARCHAR(255),
    
    -- Activity relationships
    generated_by_activity VARCHAR(255),
    
    -- OntExtract-specific properties
    document_id INTEGER,
    experiment_id INTEGER,
    version_number INTEGER,
    version_type VARCHAR(50),
    
    -- JSON metadata for additional PROV-O properties
    prov_metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create provenance_activities table
CREATE TABLE IF NOT EXISTS provenance_activities (
    id SERIAL PRIMARY KEY,
    
    -- PROV-O Core Properties
    prov_id VARCHAR(255) UNIQUE NOT NULL,
    prov_type VARCHAR(100) NOT NULL,
    prov_label VARCHAR(500),
    started_at_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at_time TIMESTAMP,
    
    -- Association with agents and plans
    was_associated_with VARCHAR(255),
    used_plan VARCHAR(255),
    
    -- OntExtract-specific properties
    processing_job_id INTEGER,
    experiment_id INTEGER,
    activity_type VARCHAR(50),
    
    -- JSON metadata for parameters and results
    activity_metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_provenance_entities_prov_id ON provenance_entities(prov_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entities_prov_type ON provenance_entities(prov_type);
CREATE INDEX IF NOT EXISTS idx_provenance_entities_document_id ON provenance_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entities_experiment_id ON provenance_entities(experiment_id);
CREATE INDEX IF NOT EXISTS idx_provenance_entities_derived_from ON provenance_entities(derived_from_entity);
CREATE INDEX IF NOT EXISTS idx_provenance_entities_generated_by ON provenance_entities(generated_by_activity);

CREATE INDEX IF NOT EXISTS idx_provenance_activities_prov_id ON provenance_activities(prov_id);
CREATE INDEX IF NOT EXISTS idx_provenance_activities_prov_type ON provenance_activities(prov_type);
CREATE INDEX IF NOT EXISTS idx_provenance_activities_processing_job_id ON provenance_activities(processing_job_id);
CREATE INDEX IF NOT EXISTS idx_provenance_activities_experiment_id ON provenance_activities(experiment_id);
CREATE INDEX IF NOT EXISTS idx_provenance_activities_activity_type ON provenance_activities(activity_type);

-- Add foreign key constraints (optional, since we use string references for PROV-O flexibility)
ALTER TABLE provenance_entities 
    ADD CONSTRAINT fk_provenance_entities_document 
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;

ALTER TABLE provenance_entities 
    ADD CONSTRAINT fk_provenance_entities_experiment 
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL;

ALTER TABLE provenance_activities 
    ADD CONSTRAINT fk_provenance_activities_processing_job 
    FOREIGN KEY (processing_job_id) REFERENCES processing_jobs(id) ON DELETE CASCADE;

ALTER TABLE provenance_activities 
    ADD CONSTRAINT fk_provenance_activities_experiment 
    FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE SET NULL;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_provenance_entities_updated_at 
    BEFORE UPDATE ON provenance_entities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provenance_activities_updated_at 
    BEFORE UPDATE ON provenance_activities 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE provenance_entities IS 'PROV-O Entity model representing first-class provenance entities';
COMMENT ON TABLE provenance_activities IS 'PROV-O Activity model representing processing activities';

COMMENT ON COLUMN provenance_entities.prov_id IS 'PROV-O Entity identifier (e.g., document_123_v2)';
COMMENT ON COLUMN provenance_entities.prov_type IS 'PROV-O Entity type (e.g., ont:Document, ont:ProcessedDocument)';
COMMENT ON COLUMN provenance_entities.derived_from_entity IS 'PROV-O wasDerivedFrom relationship';
COMMENT ON COLUMN provenance_entities.generated_by_activity IS 'PROV-O wasGeneratedBy relationship';

COMMENT ON COLUMN provenance_activities.prov_id IS 'PROV-O Activity identifier (e.g., activity_embeddings_456)';
COMMENT ON COLUMN provenance_activities.prov_type IS 'PROV-O Activity type (e.g., ont:EmbeddingsProcessing)';
COMMENT ON COLUMN provenance_activities.was_associated_with IS 'PROV-O wasAssociatedWith agent';
COMMENT ON COLUMN provenance_activities.used_plan IS 'PROV-O used plan/protocol';