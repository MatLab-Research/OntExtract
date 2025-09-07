-- Create W3C PROV-O Compliant Database Schema
-- Uses exact property names from W3C PROV-O Recommendation
-- https://www.w3.org/TR/prov-o/

-- Drop existing non-compliant tables
DROP TABLE IF EXISTS prov_relationships CASCADE;
DROP TABLE IF EXISTS prov_entities CASCADE;
DROP TABLE IF EXISTS prov_activities CASCADE;
DROP TABLE IF EXISTS prov_agents CASCADE;

-- PROV-O Agent Table
-- Represents prov:Agent with subclasses prov:Person, prov:Organization, prov:SoftwareAgent
CREATE TABLE prov_agents (
    -- Primary identifier
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Agent subclass type (exact PROV-O subclasses)
    agent_type VARCHAR(20) NOT NULL CHECK (agent_type IN ('Person', 'Organization', 'SoftwareAgent')),
    
    -- FOAF properties commonly used with prov:Agent
    foaf_name VARCHAR(255),              -- foaf:name
    foaf_givenName VARCHAR(255),         -- foaf:givenName  
    foaf_mbox VARCHAR(255),              -- foaf:mbox (email)
    foaf_homePage VARCHAR(500),          -- foaf:homePage
    
    -- Agent metadata as JSONB for flexibility
    agent_metadata JSONB DEFAULT '{}',
    
    -- Standard timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PROV-O Activity Table  
-- Represents prov:Activity with timing and relationship properties
CREATE TABLE prov_activities (
    -- Primary identifier
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Activity classification
    activity_type VARCHAR(100) NOT NULL,
    
    -- PROV-O timing properties (exact property names)
    startedAtTime TIMESTAMP WITH TIME ZONE,    -- prov:startedAtTime
    endedAtTime TIMESTAMP WITH TIME ZONE,      -- prov:endedAtTime
    
    -- PROV-O relationship properties
    wasAssociatedWith UUID REFERENCES prov_agents(agent_id),  -- prov:wasAssociatedWith
    
    -- Activity parameters and configuration
    activity_parameters JSONB DEFAULT '{}',
    
    -- Activity status and metadata
    activity_status VARCHAR(20) DEFAULT 'active' CHECK (activity_status IN ('active', 'completed', 'failed')),
    activity_metadata JSONB DEFAULT '{}',
    
    -- Standard timestamps  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint for valid time ordering
    CONSTRAINT valid_activity_duration CHECK (
        startedAtTime IS NULL OR 
        endedAtTime IS NULL OR 
        startedAtTime <= endedAtTime
    )
);

-- PROV-O Entity Table
-- Represents prov:Entity with generation and derivation properties  
CREATE TABLE prov_entities (
    -- Primary identifier
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entity classification
    entity_type VARCHAR(100) NOT NULL,
    
    -- PROV-O timing properties
    generatedAtTime TIMESTAMP WITH TIME ZONE,    -- prov:generatedAtTime
    invalidatedAtTime TIMESTAMP WITH TIME ZONE,  -- prov:invalidatedAtTime
    
    -- PROV-O relationship properties (exact property names)
    wasGeneratedBy UUID REFERENCES prov_activities(activity_id), -- prov:wasGeneratedBy
    wasAttributedTo UUID REFERENCES prov_agents(agent_id),       -- prov:wasAttributedTo
    wasDerivedFrom UUID REFERENCES prov_entities(entity_id),     -- prov:wasDerivedFrom
    
    -- Entity content and metadata
    entity_value JSONB NOT NULL DEFAULT '{}',    -- prov:value (entity content)
    entity_metadata JSONB DEFAULT '{}',
    
    -- Character position tracking for document entities
    character_start INTEGER,
    character_end INTEGER,
    
    -- Standard timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints for valid data
    CONSTRAINT valid_character_positions CHECK (
        (character_start IS NULL AND character_end IS NULL) OR 
        (character_start IS NOT NULL AND character_end IS NOT NULL AND character_start <= character_end)
    ),
    CONSTRAINT must_have_generation_provenance CHECK (wasGeneratedBy IS NOT NULL)
);

-- PROV-O Relationships Table  
-- Represents additional PROV-O relationships not captured in foreign keys
CREATE TABLE prov_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Exact PROV-O relationship types
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'wasInformedBy',     -- activity wasInformedBy activity
        'used',              -- activity used entity
        'wasStartedBy',      -- activity wasStartedBy entity  
        'wasEndedBy',        -- activity wasEndedBy entity
        'wasQuotedFrom',     -- entity wasQuotedFrom entity
        'wasRevisionOf',     -- entity wasRevisionOf entity
        'hadPrimarySource',  -- entity hadPrimarySource entity
        'alternateOf',       -- entity alternateOf entity
        'specializationOf',  -- entity specializationOf entity
        'actedOnBehalfOf'    -- agent actedOnBehalfOf agent
    )),
    
    -- Subject and object references
    subject_id UUID NOT NULL,
    subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN ('Agent', 'Activity', 'Entity')),
    object_id UUID NOT NULL, 
    object_type VARCHAR(20) NOT NULL CHECK (object_type IN ('Agent', 'Activity', 'Entity')),
    
    -- Relationship metadata
    relationship_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_prov_agents_type ON prov_agents(agent_type);
CREATE INDEX idx_prov_agents_name ON prov_agents(foaf_name);

CREATE INDEX idx_prov_activities_type ON prov_activities(activity_type);
CREATE INDEX idx_prov_activities_associated ON prov_activities(wasAssociatedWith);
CREATE INDEX idx_prov_activities_started ON prov_activities(startedAtTime);

CREATE INDEX idx_prov_entities_type ON prov_entities(entity_type);
CREATE INDEX idx_prov_entities_generated ON prov_entities(wasGeneratedBy);
CREATE INDEX idx_prov_entities_attributed ON prov_entities(wasAttributedTo);
CREATE INDEX idx_prov_entities_derived ON prov_entities(wasDerivedFrom);

CREATE INDEX idx_prov_relationships_type ON prov_relationships(relationship_type);
CREATE INDEX idx_prov_relationships_subject ON prov_relationships(subject_id, subject_type);
CREATE INDEX idx_prov_relationships_object ON prov_relationships(object_id, object_type);

-- Insert PROV-O compliant default agents
INSERT INTO prov_agents (agent_type, foaf_name, agent_metadata) VALUES 
  ('SoftwareAgent', 'LangExtract Gemini', '{
    "tool_type": "document_analyzer", 
    "model_provider": "google", 
    "model_id": "gemini-2.0-flash-exp",
    "capabilities": ["structured_extraction", "character_positioning", "semantic_analysis"],
    "version": "1.0.9"
  }'),
  ('SoftwareAgent', 'OntExtract System', '{
    "system_type": "ontology_integration",
    "features": ["JCDL", "period_aware", "human_in_loop"], 
    "version": "1.0.0"
  }'),
  ('SoftwareAgent', 'LLM Orchestrator', '{
    "orchestrator_type": "multi_provider_llm",
    "capabilities": ["tool_routing", "synthesis", "quality_control"],
    "providers": ["anthropic", "openai", "google"],
    "version": "1.0.0"
  }');

-- Verify schema creation
SELECT 'prov_agents' as table_name, COUNT(*) as record_count FROM prov_agents
UNION ALL  
SELECT 'prov_activities', COUNT(*) FROM prov_activities
UNION ALL
SELECT 'prov_entities', COUNT(*) FROM prov_entities  
UNION ALL
SELECT 'prov_relationships', COUNT(*) FROM prov_relationships;