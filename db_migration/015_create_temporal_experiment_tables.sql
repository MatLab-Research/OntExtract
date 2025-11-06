-- Migration 015: Temporal Experiment Support
-- Adds tables and columns to support temporal semantic change analysis
-- Based on "Managing Semantic Change in Research" framework

-- Add temporal and disciplinary metadata to documents for experiment tracking
CREATE TABLE IF NOT EXISTS document_temporal_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,

    -- Temporal classification
    temporal_period VARCHAR(100),  -- "Early 20th Century", "Contemporary AI Era"
    temporal_start_year INTEGER,
    temporal_end_year INTEGER,
    publication_year INTEGER,

    -- Disciplinary classification
    discipline VARCHAR(100),  -- "philosophy", "law", "economics", "computer_science", "AI"
    subdiscipline VARCHAR(100),  -- "action_theory", "agency_law", "multi_agent_systems"

    -- Semantic contribution
    key_definition TEXT,  -- How this document defines the term
    semantic_features JSONB,  -- {"intentionality": true, "autonomy": true, "legal_status": false}
    semantic_shift_type VARCHAR(50),  -- "broadening", "narrowing", "metaphorical", "continuity"

    -- Position on timeline visualization
    timeline_position INTEGER,  -- For ordering on visualization
    timeline_track VARCHAR(50),  -- Which track: "oed", "philosophy", "law", "economics", "ai"
    marker_color VARCHAR(20),  -- For discipline color-coding

    -- Metadata extraction
    extraction_method VARCHAR(50),  -- "llm", "manual", "zotero"
    extraction_confidence DECIMAL(3,2),  -- 0.00 to 1.00
    reviewed_by INTEGER REFERENCES users(id),  -- User who reviewed/approved metadata
    reviewed_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(document_id, experiment_id)
);

CREATE INDEX idx_doc_temporal_discipline ON document_temporal_metadata(discipline);
CREATE INDEX idx_doc_temporal_period ON document_temporal_metadata(temporal_period);
CREATE INDEX idx_doc_temporal_year ON document_temporal_metadata(publication_year);
CREATE INDEX idx_doc_temporal_experiment ON document_temporal_metadata(experiment_id);
CREATE INDEX idx_doc_temporal_timeline_track ON document_temporal_metadata(timeline_track);

-- Store OED timeline data extracted from OED entries
CREATE TABLE IF NOT EXISTS oed_timeline_markers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,

    -- Temporal information
    year INTEGER,
    period_label VARCHAR(100),  -- "Old English", "Middle English", "Modern English"
    century INTEGER,  -- Calculated from year

    -- Sense/definition information
    sense_number VARCHAR(20),  -- "1a", "2b", "3"
    definition TEXT NOT NULL,
    definition_short TEXT,  -- Truncated for timeline display

    -- Historical attestation
    first_recorded_use TEXT,  -- Quote showing first use
    quotation_date VARCHAR(50),
    quotation_author VARCHAR(200),
    quotation_work VARCHAR(200),

    -- Semantic classification
    semantic_category VARCHAR(100),  -- "legal", "philosophical", "computational"
    etymology_note TEXT,

    -- Timeline visualization
    marker_type VARCHAR(50),  -- "etymology", "sense", "usage"
    display_order INTEGER,

    -- Source tracking
    oed_entry_id VARCHAR(100),  -- Reference to OED entry
    extraction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    extracted_by VARCHAR(50),  -- "llm", "manual"

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(term_id, sense_number, year)
);

CREATE INDEX idx_oed_timeline_term ON oed_timeline_markers(term_id);
CREATE INDEX idx_oed_timeline_year ON oed_timeline_markers(year);
CREATE INDEX idx_oed_timeline_sense ON oed_timeline_markers(sense_number);
CREATE INDEX idx_oed_timeline_category ON oed_timeline_markers(semantic_category);

-- Store disciplinary definitions for metacognitive framework (from paper pp. 10-13)
CREATE TABLE IF NOT EXISTS term_disciplinary_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,

    -- Disciplinary context
    discipline VARCHAR(100) NOT NULL,
    definition TEXT NOT NULL,
    source_text TEXT,  -- Full citation
    source_type VARCHAR(50),  -- "dictionary", "encyclopedia", "textbook", "paper"

    -- Temporal context
    period_label VARCHAR(100),
    start_year INTEGER,
    end_year INTEGER,

    -- Semantic analysis (for comparison tables)
    key_features JSONB,  -- {"intentionality": true, "moral_responsibility": true, "legal_authority": false}
    distinguishing_features TEXT,  -- What makes this definition unique
    parallel_meanings JSONB,  -- References to other discipline meanings at same time
    potential_confusion TEXT,  -- Notes on interdisciplinary tensions

    -- Document reference
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,

    -- Metacognitive framework fields (Boon & Van Baalen 2018)
    resolution_notes TEXT,  -- How to resolve confusion with other disciplines

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_disciplinary_def_term ON term_disciplinary_definitions(term_id);
CREATE INDEX idx_disciplinary_def_experiment ON term_disciplinary_definitions(experiment_id);
CREATE INDEX idx_disciplinary_def_discipline ON term_disciplinary_definitions(discipline);
CREATE INDEX idx_disciplinary_def_document ON term_disciplinary_definitions(document_id);

-- Track semantic shifts identified in temporal analysis
CREATE TABLE IF NOT EXISTS semantic_shift_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    term_id UUID NOT NULL REFERENCES terms(id) ON DELETE CASCADE,

    -- Shift identification
    shift_type VARCHAR(50) NOT NULL,  -- "diachronic", "polysemy", "interdisciplinary", "disciplinary_capture"
    from_period VARCHAR(100),
    to_period VARCHAR(100),
    from_discipline VARCHAR(100),
    to_discipline VARCHAR(100),

    -- Shift description
    description TEXT NOT NULL,
    evidence TEXT,  -- Supporting quotes or analysis

    -- Linked entities
    from_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    to_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    from_definition_id UUID REFERENCES term_disciplinary_definitions(id) ON DELETE SET NULL,
    to_definition_id UUID REFERENCES term_disciplinary_definitions(id) ON DELETE SET NULL,

    -- Visualization
    edge_type VARCHAR(50),  -- For timeline graph: "continuity", "broadening", "shift", "metaphorical"
    edge_label TEXT,  -- Short description for graph edge

    -- Analysis metadata
    detected_by VARCHAR(50),  -- "llm", "manual"
    confidence DECIMAL(3,2),  -- 0.00 to 1.00

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_semantic_shift_experiment ON semantic_shift_analysis(experiment_id);
CREATE INDEX idx_semantic_shift_term ON semantic_shift_analysis(term_id);
CREATE INDEX idx_semantic_shift_type ON semantic_shift_analysis(shift_type);

-- Add temporal experiment configuration to experiments.configuration JSON
-- No schema change needed - will use existing configuration column with structure:
-- {
--   "experiment_type": "temporal_evolution",
--   "anchor_term_id": "<uuid>",
--   "temporal_scope": {
--     "start_year": 1850,
--     "end_year": 2024,
--     "focus_disciplines": ["philosophy", "law", "economics", "AI"]
--   },
--   "visualization_config": {
--     "timeline_type": "horizontal_parallel",
--     "graph_layout": "temporal",
--     "show_oed_track": true,
--     "track_colors": {
--       "oed": "#6c757d",
--       "philosophy": "#3498db",
--       "law": "#e74c3c",
--       "economics": "#2ecc71",
--       "ai": "#9b59b6"
--     }
--   }
-- }

COMMENT ON TABLE document_temporal_metadata IS 'Temporal and disciplinary metadata for documents in semantic change experiments';
COMMENT ON TABLE oed_timeline_markers IS 'Historical timeline data extracted from OED entries for anchor terms';
COMMENT ON TABLE term_disciplinary_definitions IS 'Disciplinary definitions for metacognitive framework comparison tables';
COMMENT ON TABLE semantic_shift_analysis IS 'Identified semantic shifts and evolution patterns';
