-- Migration: Add LLM Orchestration Logging Tables
-- Creates PROV-O compliant tables for logging orchestration decisions, tool execution, and consensus validation
-- Date: 2026-01-26

BEGIN;

-- Create orchestration_decisions table
CREATE TABLE IF NOT EXISTS orchestration_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- PROV-O Activity metadata
    activity_type VARCHAR(50) NOT NULL DEFAULT 'llm_orchestration',
    started_at_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ended_at_time TIMESTAMPTZ,
    activity_status VARCHAR(20) DEFAULT 'completed',
    
    -- Document context
    document_id INTEGER REFERENCES documents(id),
    experiment_id INTEGER REFERENCES experiments(id),
    term_text VARCHAR(255),
    
    -- Input metadata that influenced decision
    input_metadata JSONB,
    document_characteristics JSONB,
    
    -- LLM orchestration details
    orchestrator_provider VARCHAR(50),
    orchestrator_model VARCHAR(100),
    orchestrator_prompt TEXT,
    orchestrator_response TEXT,
    orchestrator_response_time_ms INTEGER,
    
    -- Decision outputs
    selected_tools TEXT[],
    embedding_model VARCHAR(100),
    processing_strategy VARCHAR(50),
    expected_runtime_seconds INTEGER,
    
    -- Confidence and reasoning
    decision_confidence DECIMAL(4,3) CHECK (decision_confidence >= 0 AND decision_confidence <= 1),
    reasoning_summary TEXT,
    decision_factors JSONB,
    
    -- Validation and outcomes
    decision_validated BOOLEAN,
    actual_runtime_seconds INTEGER,
    tool_execution_success JSONB,
    
    -- PROV-O relationships
    was_associated_with UUID REFERENCES analysis_agents(id),
    used_entity UUID REFERENCES term_versions(id),
    
    -- Audit trail
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    
    CONSTRAINT orchestration_decisions_activity_status_check 
        CHECK (activity_status IN ('running', 'completed', 'error', 'timeout'))
);

-- Create indexes for orchestration_decisions
CREATE INDEX IF NOT EXISTS idx_orchestration_decisions_status ON orchestration_decisions(activity_status);
CREATE INDEX IF NOT EXISTS idx_orchestration_decisions_term_time ON orchestration_decisions(term_text, created_at);
CREATE INDEX IF NOT EXISTS idx_orchestration_decisions_experiment ON orchestration_decisions(experiment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_orchestration_decisions_document ON orchestration_decisions(document_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_decisions_agent ON orchestration_decisions(was_associated_with);


-- Create tool_execution_logs table
CREATE TABLE IF NOT EXISTS tool_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to parent orchestration decision
    orchestration_decision_id UUID NOT NULL REFERENCES orchestration_decisions(id) ON DELETE CASCADE,
    
    -- Tool execution details
    tool_name VARCHAR(50) NOT NULL,
    tool_version VARCHAR(50),
    execution_order INTEGER,
    
    -- Execution timing
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,
    
    -- Execution results
    execution_status VARCHAR(20) DEFAULT 'running',
    output_data JSONB,
    error_message TEXT,
    
    -- Performance metrics
    memory_usage_mb INTEGER,
    cpu_usage_percent DECIMAL(5,2),
    output_quality_score DECIMAL(4,3) CHECK (output_quality_score >= 0 AND output_quality_score <= 1),
    
    CONSTRAINT tool_execution_logs_status_check 
        CHECK (execution_status IN ('running', 'completed', 'error', 'timeout', 'skipped'))
);

-- Create indexes for tool_execution_logs
CREATE INDEX IF NOT EXISTS idx_tool_execution_logs_decision_order ON tool_execution_logs(orchestration_decision_id, execution_order);
CREATE INDEX IF NOT EXISTS idx_tool_execution_logs_tool_name ON tool_execution_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_execution_logs_status ON tool_execution_logs(execution_status);


-- Create multi_model_consensus table
CREATE TABLE IF NOT EXISTS multi_model_consensus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to parent orchestration
    orchestration_decision_id UUID NOT NULL REFERENCES orchestration_decisions(id) ON DELETE CASCADE,
    
    -- Consensus process metadata
    validation_type VARCHAR(50) DEFAULT 'multi_model_consensus',
    models_involved TEXT[],
    consensus_method VARCHAR(50),
    
    -- Model-specific results
    model_responses JSONB,
    model_confidence_scores JSONB,
    model_agreement_matrix JSONB,
    
    -- Consensus outcomes
    consensus_reached BOOLEAN,
    consensus_confidence DECIMAL(4,3) CHECK (consensus_confidence >= 0 AND consensus_confidence <= 1),
    final_decision JSONB,
    disagreement_areas JSONB,
    
    -- Timing and metadata
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    total_processing_time_ms INTEGER
);

-- Create indexes for multi_model_consensus
CREATE INDEX IF NOT EXISTS idx_multi_model_consensus_decision ON multi_model_consensus(orchestration_decision_id);
CREATE INDEX IF NOT EXISTS idx_multi_model_consensus_reached ON multi_model_consensus(consensus_reached);

-- Add comments for documentation
COMMENT ON TABLE orchestration_decisions IS 'PROV-O compliant logging of LLM orchestration decisions for tool selection and coordination';
COMMENT ON TABLE tool_execution_logs IS 'Detailed logs of individual NLP tool execution with performance metrics';
COMMENT ON TABLE multi_model_consensus IS 'Multi-model validation and consensus decision logging';

COMMENT ON COLUMN orchestration_decisions.input_metadata IS 'Document metadata that influenced tool selection (year, domain, format, length)';
COMMENT ON COLUMN orchestration_decisions.decision_factors IS 'Structured reasoning components for decision analysis';
COMMENT ON COLUMN orchestration_decisions.tool_execution_success IS 'Per-tool success rates and validation results';

COMMENT ON COLUMN tool_execution_logs.output_quality_score IS 'Quality assessment of tool output (0.0 = poor, 1.0 = excellent)';
COMMENT ON COLUMN tool_execution_logs.execution_order IS 'Order in processing pipeline (0 = first, higher = later)';

COMMENT ON COLUMN multi_model_consensus.model_agreement_matrix IS 'Pairwise agreement scores between models';
COMMENT ON COLUMN multi_model_consensus.disagreement_areas IS 'Specific areas where models disagreed';

COMMIT;

-- Verify tables were created
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('orchestration_decisions', 'tool_execution_logs', 'multi_model_consensus')
ORDER BY tablename;