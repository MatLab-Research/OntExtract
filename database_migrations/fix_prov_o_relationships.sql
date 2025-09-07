-- Fix PROV-O Relationships table
-- Create the relationships table without complex CHECK constraints

-- Drop the table if it exists and recreate it
DROP TABLE IF EXISTS prov_relationships CASCADE;

CREATE TABLE prov_relationships (
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for the relationships table
CREATE INDEX idx_prov_relationships_type ON prov_relationships(relationship_type);
CREATE INDEX idx_prov_relationships_subject ON prov_relationships(subject_id, subject_type);
CREATE INDEX idx_prov_relationships_object ON prov_relationships(object_id, object_type);

-- Verify all tables exist
SELECT 'prov_agents' as table_name, COUNT(*) as record_count FROM prov_agents
UNION ALL
SELECT 'prov_activities', COUNT(*) FROM prov_activities  
UNION ALL
SELECT 'prov_entities', COUNT(*) FROM prov_entities
UNION ALL
SELECT 'prov_relationships', COUNT(*) FROM prov_relationships;