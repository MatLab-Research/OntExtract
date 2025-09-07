-- PROV-O Database Tables Migration
-- Creates the necessary tables for PROV-O tracking functionality

-- PROV-O Agents (software, services, users)
CREATE TABLE IF NOT EXISTS prov_agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN ('software', 'service', 'person', 'organization')),
    agent_name VARCHAR(200) NOT NULL,
    agent_description TEXT,
    agent_version VARCHAR(50),
    agent_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_agent_name CHECK (LENGTH(agent_name) >= 1)
);

-- PROV-O Activities (processes, analyses, transformations)
CREATE TABLE IF NOT EXISTS prov_activities (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_type VARCHAR(50) NOT NULL,
    activity_name VARCHAR(200) NOT NULL,
    activity_description TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    activity_metadata JSONB DEFAULT '{}',
    associated_agent_id UUID REFERENCES prov_agents(agent_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_duration CHECK (started_at IS NULL OR ended_at IS NULL OR started_at <= ended_at),
    CONSTRAINT valid_activity_name CHECK (LENGTH(activity_name) >= 1)
);

-- PROV-O Entities (data, documents, results)
CREATE TABLE IF NOT EXISTS prov_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_content JSONB NOT NULL DEFAULT '{}',
    entity_metadata JSONB DEFAULT '{}',
    character_start INTEGER,
    character_end INTEGER,
    generated_by_activity UUID REFERENCES prov_activities(activity_id) ON DELETE CASCADE NOT NULL,
    derived_from_entity UUID REFERENCES prov_entities(entity_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_character_positions CHECK (
        (character_start IS NULL AND character_end IS NULL) OR 
        (character_start IS NOT NULL AND character_end IS NOT NULL AND character_start <= character_end)
    ),
    CONSTRAINT must_have_provenance CHECK (generated_by_activity IS NOT NULL)
);

-- PROV-O Relationships (wasGeneratedBy, wasAssociatedWith, wasDerivedFrom, etc.)
CREATE TABLE IF NOT EXISTS prov_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'wasGeneratedBy', 'wasAssociatedWith', 'wasDerivedFrom', 'wasInformedBy',
        'wasAttributedTo', 'wasInfluencedBy', 'used', 'hadMember'
    )),
    subject_id UUID NOT NULL,
    subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN ('agent', 'activity', 'entity')),
    object_id UUID NOT NULL,
    object_type VARCHAR(20) NOT NULL CHECK (object_type IN ('agent', 'activity', 'entity')),
    relationship_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure valid subject/object references
    CONSTRAINT valid_subject_agent CHECK (
        subject_type != 'agent' OR 
        EXISTS (SELECT 1 FROM prov_agents WHERE agent_id = subject_id)
    ),
    CONSTRAINT valid_subject_activity CHECK (
        subject_type != 'activity' OR 
        EXISTS (SELECT 1 FROM prov_activities WHERE activity_id = subject_id)
    ),
    CONSTRAINT valid_subject_entity CHECK (
        subject_type != 'entity' OR 
        EXISTS (SELECT 1 FROM prov_entities WHERE entity_id = subject_id)
    ),
    CONSTRAINT valid_object_agent CHECK (
        object_type != 'agent' OR 
        EXISTS (SELECT 1 FROM prov_agents WHERE agent_id = object_id)
    ),
    CONSTRAINT valid_object_activity CHECK (
        object_type != 'activity' OR 
        EXISTS (SELECT 1 FROM prov_activities WHERE activity_id = object_id)
    ),
    CONSTRAINT valid_object_entity CHECK (
        object_type != 'entity' OR 
        EXISTS (SELECT 1 FROM prov_entities WHERE entity_id = object_id)
    )
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_prov_agents_type ON prov_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_prov_agents_name ON prov_agents(agent_name);

CREATE INDEX IF NOT EXISTS idx_prov_activities_type ON prov_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_prov_activities_agent ON prov_activities(associated_agent_id);
CREATE INDEX IF NOT EXISTS idx_prov_activities_started ON prov_activities(started_at);

CREATE INDEX IF NOT EXISTS idx_prov_entities_type ON prov_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_prov_entities_activity ON prov_entities(generated_by_activity);
CREATE INDEX IF NOT EXISTS idx_prov_entities_derived ON prov_entities(derived_from_entity);
CREATE INDEX IF NOT EXISTS idx_prov_entities_positions ON prov_entities(character_start, character_end);

CREATE INDEX IF NOT EXISTS idx_prov_relationships_type ON prov_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_prov_relationships_subject ON prov_relationships(subject_id, subject_type);
CREATE INDEX IF NOT EXISTS idx_prov_relationships_object ON prov_relationships(object_id, object_type);

-- Insert default agents for system components
INSERT INTO prov_agents (agent_type, agent_name, agent_description, agent_version, agent_metadata) 
VALUES 
    ('software', 'LangExtract', 'Google LangExtract library for structured document analysis', '1.0.9', '{"provider": "google", "model": "gemini-2.0-flash-exp"}'),
    ('software', 'OntExtract', 'Document processing and ontology integration system', '1.0.0', '{"features": ["JCDL", "period_aware", "human_in_loop"]}'),
    ('service', 'LLM Orchestration', 'Intelligent tool selection and coordination service', '1.0.0', '{"capabilities": ["tool_routing", "synthesis", "quality_control"]}')
ON CONFLICT DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_prov_agents_updated_at BEFORE UPDATE ON prov_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;