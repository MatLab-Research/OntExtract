-- Migration: Add Term Management Tables for Semantic Change Analysis
-- Based on PROV-O ontology framework and research design requirements
-- Created: 2025-08-24

-- =====================================
-- Core Terms Table
-- =====================================
CREATE TABLE IF NOT EXISTS terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_text VARCHAR(255) NOT NULL,
    entry_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' NOT NULL CHECK (status IN ('active', 'provisional', 'deprecated')),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    description TEXT,
    etymology TEXT,
    notes TEXT,
    
    -- Research context
    research_domain VARCHAR(100),
    selection_rationale TEXT, -- Why this term was chosen as anchor
    historical_significance TEXT,
    
    UNIQUE(term_text, created_by) -- Prevent duplicate terms per user
);

-- =====================================
-- Term Versions Table (prov:Entity)
-- =====================================
CREATE TABLE IF NOT EXISTS term_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID REFERENCES terms(id) ON DELETE CASCADE NOT NULL,
    
    -- Temporal context
    temporal_period VARCHAR(50) NOT NULL, -- "2000", "1800-1850", etc.
    temporal_start_year INTEGER,
    temporal_end_year INTEGER,
    
    -- Semantic content
    meaning_description TEXT NOT NULL,
    context_anchor JSON, -- Array of semantically related terms
    original_context_anchor JSON, -- Preserved original neighborhood
    
    -- Fuzziness and uncertainty metrics
    fuzziness_score DECIMAL(4,3) CHECK (fuzziness_score >= 0 AND fuzziness_score <= 1),
    confidence_level VARCHAR(10) DEFAULT 'medium' CHECK (confidence_level IN ('high', 'medium', 'low')),
    certainty_notes TEXT, -- Explanations of uncertainty
    
    -- Corpus and source information
    corpus_source VARCHAR(100), -- "COHA", "Google_Books", "Custom", etc.
    source_documents JSON, -- References to specific documents/corpora
    extraction_method VARCHAR(50), -- "manual", "bert_embedding", "frequency_analysis"
    
    -- PROV-O compliance
    generated_at_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    was_derived_from UUID REFERENCES term_versions(id), -- Parent version
    derivation_type VARCHAR(30), -- "revision", "specialization", "merge"
    
    -- Version control
    version_number INTEGER DEFAULT 1,
    is_current BOOLEAN DEFAULT true,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Semantic neighborhood analysis
    neighborhood_overlap DECIMAL(4,3) CHECK (neighborhood_overlap >= 0 AND neighborhood_overlap <= 1),
    positional_change DECIMAL(4,3) CHECK (positional_change >= 0 AND positional_change <= 1),
    similarity_reduction DECIMAL(4,3) CHECK (similarity_reduction >= 0 AND similarity_reduction <= 1)
);

-- =====================================
-- Semantic Drift Activities Table (prov:Activity)
-- =====================================
CREATE TABLE IF NOT EXISTS semantic_drift_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_type VARCHAR(50) DEFAULT 'semantic_drift_detection' NOT NULL,
    
    -- Temporal scope
    start_period VARCHAR(50) NOT NULL,
    end_period VARCHAR(50) NOT NULL,
    temporal_scope_years INTEGER[], -- Array of years covered
    
    -- PROV-O relationships
    used_entity UUID REFERENCES term_versions(id) ON DELETE SET NULL, -- Input version
    generated_entity UUID REFERENCES term_versions(id) ON DELETE SET NULL, -- Output version
    was_associated_with UUID, -- References agents table (to be created)
    
    -- Drift detection metrics
    drift_metrics JSON, -- Detailed numerical results
    detection_algorithm VARCHAR(100), -- "HistBERT", "Word2Vec", "Manual"
    algorithm_parameters JSON, -- Configuration used
    
    -- Activity metadata
    started_at_time TIMESTAMP WITH TIME ZONE,
    ended_at_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    activity_status VARCHAR(20) DEFAULT 'completed' CHECK (activity_status IN ('running', 'completed', 'error', 'provisional')),
    
    -- Results
    drift_detected BOOLEAN DEFAULT false,
    drift_magnitude DECIMAL(4,3) CHECK (drift_magnitude >= 0 AND drift_magnitude <= 1),
    drift_type VARCHAR(30), -- "gradual", "sudden", "domain_shift", "semantic_bleaching"
    evidence_summary TEXT,
    
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- Analysis Agents Table (prov:Agent)
-- =====================================
CREATE TABLE IF NOT EXISTS analysis_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(20) NOT NULL CHECK (agent_type IN ('SoftwareAgent', 'Person', 'Organization')),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    
    -- For software agents
    algorithm_type VARCHAR(100), -- "HistBERT", "Word2Vec", "Manual_Curation"
    model_parameters JSON,
    training_data VARCHAR(200),
    
    -- For human agents
    expertise_domain VARCHAR(100),
    institutional_affiliation VARCHAR(200),
    
    -- Agent metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- Self-reference for user agents
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- =====================================
-- Context Anchors Table (for searchable/autocomplete)
-- =====================================
CREATE TABLE IF NOT EXISTS context_anchors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anchor_term VARCHAR(255) NOT NULL,
    frequency INTEGER DEFAULT 1,
    first_used_in UUID REFERENCES term_versions(id),
    last_used_in UUID REFERENCES term_versions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(anchor_term)
);

-- =====================================
-- Term Version Context Anchors (Many-to-Many)
-- =====================================
CREATE TABLE IF NOT EXISTS term_version_anchors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_version_id UUID REFERENCES term_versions(id) ON DELETE CASCADE,
    context_anchor_id UUID REFERENCES context_anchors(id) ON DELETE CASCADE,
    similarity_score DECIMAL(4,3) CHECK (similarity_score >= 0 AND similarity_score <= 1),
    rank_in_neighborhood INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(term_version_id, context_anchor_id)
);

-- =====================================
-- Fuzziness Score Adjustments (audit trail)
-- =====================================
CREATE TABLE IF NOT EXISTS fuzziness_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_version_id UUID REFERENCES term_versions(id) ON DELETE CASCADE,
    original_score DECIMAL(4,3) NOT NULL,
    adjusted_score DECIMAL(4,3) NOT NULL,
    adjustment_reason TEXT NOT NULL,
    adjusted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- Provenance Chains (for complex derivations)
-- =====================================
CREATE TABLE IF NOT EXISTS provenance_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID, -- Can reference term_versions or other entities
    entity_type VARCHAR(30) NOT NULL, -- "term_version", "activity", "agent"
    
    -- Qualified derivation details
    was_derived_from UUID,
    derivation_activity UUID REFERENCES semantic_drift_activities(id),
    derivation_metadata JSON, -- Additional context about the derivation
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- Indexes for Performance
-- =====================================

-- Terms
CREATE INDEX IF NOT EXISTS idx_terms_text ON terms(term_text);
CREATE INDEX IF NOT EXISTS idx_terms_status ON terms(status);
CREATE INDEX IF NOT EXISTS idx_terms_created_by ON terms(created_by);
CREATE INDEX IF NOT EXISTS idx_terms_research_domain ON terms(research_domain);

-- Term Versions
CREATE INDEX IF NOT EXISTS idx_term_versions_term_id ON term_versions(term_id);
CREATE INDEX IF NOT EXISTS idx_term_versions_temporal_period ON term_versions(temporal_period);
CREATE INDEX IF NOT EXISTS idx_term_versions_temporal_years ON term_versions(temporal_start_year, temporal_end_year);
CREATE INDEX IF NOT EXISTS idx_term_versions_current ON term_versions(is_current) WHERE is_current = true;
CREATE INDEX IF NOT EXISTS idx_term_versions_fuzziness ON term_versions(fuzziness_score);
CREATE INDEX IF NOT EXISTS idx_term_versions_corpus ON term_versions(corpus_source);

-- Semantic Drift Activities
CREATE INDEX IF NOT EXISTS idx_drift_activities_periods ON semantic_drift_activities(start_period, end_period);
CREATE INDEX IF NOT EXISTS idx_drift_activities_used_entity ON semantic_drift_activities(used_entity);
CREATE INDEX IF NOT EXISTS idx_drift_activities_generated_entity ON semantic_drift_activities(generated_entity);
CREATE INDEX IF NOT EXISTS idx_drift_activities_agent ON semantic_drift_activities(was_associated_with);
CREATE INDEX IF NOT EXISTS idx_drift_activities_status ON semantic_drift_activities(activity_status);

-- Context Anchors
CREATE INDEX IF NOT EXISTS idx_context_anchors_term ON context_anchors(anchor_term);
CREATE INDEX IF NOT EXISTS idx_context_anchors_frequency ON context_anchors(frequency DESC);

-- Term Version Anchors
CREATE INDEX IF NOT EXISTS idx_term_version_anchors_version ON term_version_anchors(term_version_id);
CREATE INDEX IF NOT EXISTS idx_term_version_anchors_anchor ON term_version_anchors(context_anchor_id);
CREATE INDEX IF NOT EXISTS idx_term_version_anchors_similarity ON term_version_anchors(similarity_score DESC);

-- Analysis Agents
CREATE INDEX IF NOT EXISTS idx_analysis_agents_type ON analysis_agents(agent_type);
CREATE INDEX IF NOT EXISTS idx_analysis_agents_active ON analysis_agents(is_active) WHERE is_active = true;

-- Fuzziness Adjustments
CREATE INDEX IF NOT EXISTS idx_fuzziness_adjustments_version ON fuzziness_adjustments(term_version_id);
CREATE INDEX IF NOT EXISTS idx_fuzziness_adjustments_user ON fuzziness_adjustments(adjusted_by);

-- =====================================
-- Triggers for Maintenance
-- =====================================

-- Update updated_at timestamp on terms
CREATE OR REPLACE FUNCTION update_terms_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_terms_updated_at
    BEFORE UPDATE ON terms
    FOR EACH ROW
    EXECUTE FUNCTION update_terms_updated_at();

-- Maintain context_anchors frequency
CREATE OR REPLACE FUNCTION update_context_anchor_frequency()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO context_anchors (anchor_term, frequency, first_used_in, last_used_in)
        VALUES ((SELECT anchor_term FROM context_anchors WHERE id = NEW.context_anchor_id), 1, NEW.term_version_id, NEW.term_version_id)
        ON CONFLICT (anchor_term) DO UPDATE SET
            frequency = context_anchors.frequency + 1,
            last_used_in = NEW.term_version_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE context_anchors SET frequency = frequency - 1 
        WHERE id = OLD.context_anchor_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_context_anchor_frequency
    AFTER INSERT OR DELETE ON term_version_anchors
    FOR EACH ROW
    EXECUTE FUNCTION update_context_anchor_frequency();

-- =====================================
-- Initial Data
-- =====================================

-- Create default software agent for manual entry
INSERT INTO analysis_agents (agent_type, name, description, algorithm_type, version) 
VALUES ('Person', 'Manual Curation', 'Human curator performing manual semantic analysis', 'Manual_Curation', '1.0')
ON CONFLICT DO NOTHING;

-- Example PROV-O based agents (from research design)
INSERT INTO analysis_agents (agent_type, name, description, algorithm_type, version)
VALUES 
    ('SoftwareAgent', 'HistBERT Temporal Embedding Alignment', 'Historical BERT model for temporal semantic alignment', 'HistBERT', '1.0'),
    ('SoftwareAgent', 'Word2Vec Diachronic Analysis', 'Word2Vec model trained on temporal corpora', 'Word2Vec', '1.0')
ON CONFLICT DO NOTHING;

-- Add comments to tables for documentation
COMMENT ON TABLE terms IS 'Core terms table storing anchor terms for semantic change analysis';
COMMENT ON TABLE term_versions IS 'PROV-O Entity: Different temporal versions of term meanings';  
COMMENT ON TABLE semantic_drift_activities IS 'PROV-O Activity: Semantic drift detection activities between time periods';
COMMENT ON TABLE analysis_agents IS 'PROV-O Agent: Software algorithms and human curators responsible for analysis';
COMMENT ON TABLE context_anchors IS 'Reusable context anchor terms for autocomplete and consistency';
COMMENT ON TABLE fuzziness_adjustments IS 'Audit trail for manual adjustments to fuzziness scores';
COMMENT ON TABLE provenance_chains IS 'Complex provenance relationships for detailed audit trails';