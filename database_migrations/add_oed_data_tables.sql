-- Database migration to add OED data storage for semantic evolution visualization
-- Adds tables to store OED etymology, definitions, and historical quotations
-- Compatible with existing Term and TermVersion models

-- OED Etymology table - PROV-O Entity: stores word origin and etymology information
CREATE TABLE oed_etymology (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    etymology_text TEXT,
    origin_language VARCHAR(50),
    first_recorded_year INTEGER,
    etymology_confidence VARCHAR(20) DEFAULT 'medium',
    -- JSON fields for structured data that doesn't violate OED license
    language_family JSON, -- e.g. {"family": "Germanic", "branch": "West Germanic"}
    root_analysis JSON,   -- e.g. {"roots": ["ag-", "ent"], "meaning": "to drive, to act"}
    morphology JSON,      -- e.g. {"suffixes": ["-ent"], "type": "agent_noun"}
    -- PROV-O Entity metadata
    generated_at_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    was_attributed_to VARCHAR(100) DEFAULT 'OED_API_Service',
    was_derived_from VARCHAR(200), -- OED entry ID or source reference
    derivation_type VARCHAR(50) DEFAULT 'etymology_extraction',
    source_version VARCHAR(50), -- OED version/edition
    -- System metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- OED Definitions table - PROV-O Entity: stores historical definitions with temporal context
CREATE TABLE oed_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    definition_number VARCHAR(10), -- e.g. "1.a", "2.b"
    definition_text TEXT NOT NULL,
    first_cited_year INTEGER,
    last_cited_year INTEGER,
    part_of_speech VARCHAR(30),
    domain_label VARCHAR(100), -- e.g. "Law", "Philosophy", "Computing"
    status VARCHAR(20) DEFAULT 'current', -- 'current', 'historical', 'obsolete'
    -- Summary statistics (allowed under fair use)
    quotation_count INTEGER,
    sense_frequency_rank INTEGER,
    -- Temporal context
    historical_period VARCHAR(50), -- aligned with existing temporal_period
    period_start_year INTEGER,
    period_end_year INTEGER,
    -- PROV-O Entity metadata
    generated_at_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    was_attributed_to VARCHAR(100) DEFAULT 'OED_API_Service',
    was_derived_from VARCHAR(200), -- OED entry ID and sense reference
    derivation_type VARCHAR(50) DEFAULT 'definition_extraction',
    definition_confidence VARCHAR(20) DEFAULT 'high',
    -- System metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    -- Indexes for semantic evolution queries
    CONSTRAINT check_definition_confidence CHECK (definition_confidence IN ('high', 'medium', 'low')),
    CONSTRAINT check_definition_status CHECK (status IN ('current', 'historical', 'obsolete'))
);

-- OED Historical Statistics table - PROV-O Activity: aggregated data calculation for visualization
CREATE TABLE oed_historical_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    time_period VARCHAR(50) NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    -- Usage statistics (aggregated, non-infringing)
    definition_count INTEGER DEFAULT 0,
    sense_count INTEGER DEFAULT 0,
    quotation_span_years INTEGER, -- latest - earliest quotation
    earliest_quotation_year INTEGER,
    latest_quotation_year INTEGER,
    -- Evolution indicators
    semantic_stability_score NUMERIC(4,3), -- calculated from definition changes
    domain_shift_indicator BOOLEAN DEFAULT FALSE,
    part_of_speech_changes JSON, -- e.g. ["noun", "verb"] for flexibility changes
    -- PROV-O Activity metadata
    started_at_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    ended_at_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    was_associated_with VARCHAR(100) DEFAULT 'Statistical_Analysis_Service',
    used_entity JSON, -- References to OED definitions and quotations used
    generated_entity VARCHAR(200), -- This statistics record itself
    oed_edition VARCHAR(50),
    -- System metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    -- Constraints
    CONSTRAINT check_semantic_stability CHECK (semantic_stability_score >= 0 AND semantic_stability_score <= 1),
    CONSTRAINT unique_term_period UNIQUE (term_id, time_period)
);

-- OED Quotation Summary table - PROV-O Entity: essential quotation metadata only
CREATE TABLE oed_quotation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    oed_definition_id UUID REFERENCES oed_definitions(id) ON DELETE CASCADE,
    quotation_year INTEGER,
    author_name VARCHAR(200),
    work_title VARCHAR(300),
    domain_context VARCHAR(100), -- inferred domain from work
    usage_type VARCHAR(50), -- e.g. "literal", "metaphorical", "technical"
    -- Metadata only, no full text to respect licensing
    has_technical_usage BOOLEAN DEFAULT FALSE,
    represents_semantic_shift BOOLEAN DEFAULT FALSE,
    chronological_rank INTEGER, -- position in temporal sequence
    -- PROV-O Entity metadata
    generated_at_time TIMESTAMP WITH TIME ZONE DEFAULT now(),
    was_attributed_to VARCHAR(100) DEFAULT 'OED_Quotation_Extractor',
    was_derived_from VARCHAR(200), -- Original OED quotation reference
    derivation_type VARCHAR(50) DEFAULT 'metadata_extraction',
    -- System metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for performance
CREATE INDEX idx_oed_etymology_term_id ON oed_etymology(term_id);
CREATE INDEX idx_oed_definitions_term_id ON oed_definitions(term_id);
CREATE INDEX idx_oed_definitions_temporal ON oed_definitions(first_cited_year, last_cited_year);
CREATE INDEX idx_oed_definitions_period ON oed_definitions(historical_period);
CREATE INDEX idx_oed_historical_stats_term_period ON oed_historical_stats(term_id, start_year, end_year);
CREATE INDEX idx_oed_quotations_term_year ON oed_quotation_summaries(term_id, quotation_year);
CREATE INDEX idx_oed_quotations_chronological ON oed_quotation_summaries(term_id, chronological_rank);

-- Create view for semantic evolution visualization
CREATE OR REPLACE VIEW semantic_evolution_with_oed AS
SELECT 
    t.id AS term_id,
    t.term_text,
    tv.id AS version_id,
    tv.temporal_period,
    tv.temporal_start_year,
    tv.temporal_end_year,
    tv.meaning_description,
    tv.source_citation,
    tv.context_anchor,
    tv.confidence_level,
    -- OED Etymology data
    oe.etymology_text,
    oe.origin_language,
    oe.first_recorded_year,
    oe.language_family,
    -- OED Historical statistics
    ohs.definition_count,
    ohs.sense_count,
    ohs.quotation_span_years,
    ohs.earliest_quotation_year,
    ohs.latest_quotation_year,
    ohs.semantic_stability_score AS oed_stability_score,
    ohs.domain_shift_indicator,
    -- Aggregate definition data
    (SELECT COUNT(*) FROM oed_definitions od WHERE od.term_id = t.id) AS total_oed_definitions,
    (SELECT COUNT(*) FROM oed_quotation_summaries oqs WHERE oqs.term_id = t.id) AS total_quotation_references
FROM terms t
LEFT JOIN term_versions tv ON t.id = tv.term_id
LEFT JOIN oed_etymology oe ON t.id = oe.term_id
LEFT JOIN oed_historical_stats ohs ON t.id = ohs.term_id 
    AND tv.temporal_period = ohs.time_period
ORDER BY t.term_text, tv.temporal_start_year;

-- Add helpful comments
COMMENT ON TABLE oed_etymology IS 'OED etymology data for terms - origin and language family information';
COMMENT ON TABLE oed_definitions IS 'Historical definitions from OED with temporal context';
COMMENT ON TABLE oed_historical_stats IS 'Aggregated statistics for semantic evolution analysis';
COMMENT ON TABLE oed_quotation_summaries IS 'Essential quotation metadata without full text';
COMMENT ON VIEW semantic_evolution_with_oed IS 'Combined view for semantic evolution visualization including OED data';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON oed_etymology, oed_definitions, oed_historical_stats, oed_quotation_summaries TO ontextract_user;
-- GRANT SELECT ON semantic_evolution_with_oed TO ontextract_user;