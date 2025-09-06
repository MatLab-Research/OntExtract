-- Migration: Add Human-in-the-Loop Orchestration Feedback Tables
-- Creates tables for researcher feedback, learning patterns, and manual overrides
-- Date: 2026-01-26

BEGIN;

-- Create orchestration_feedback table
CREATE TABLE IF NOT EXISTS orchestration_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to original decision
    orchestration_decision_id UUID NOT NULL REFERENCES orchestration_decisions(id) ON DELETE CASCADE,
    
    -- Researcher providing feedback
    researcher_id INTEGER NOT NULL REFERENCES users(id),
    researcher_expertise JSONB,
    
    -- Feedback metadata
    feedback_type VARCHAR(50) NOT NULL,
    feedback_scope VARCHAR(50),
    
    -- Original vs. Preferred decisions
    original_decision JSONB,
    researcher_preference JSONB,
    
    -- Detailed feedback
    agreement_level VARCHAR(20),
    confidence_assessment DECIMAL(4,3) CHECK (confidence_assessment >= 0 AND confidence_assessment <= 1),
    
    reasoning TEXT NOT NULL,
    domain_specific_factors JSONB,
    
    -- Suggested improvements
    suggested_tools TEXT[],
    suggested_embedding_model VARCHAR(100),
    suggested_processing_strategy VARCHAR(50),
    alternative_reasoning TEXT,
    
    -- Learning integration
    feedback_status VARCHAR(20) DEFAULT 'pending',
    integration_notes TEXT,
    
    -- Impact tracking
    subsequent_decisions_influenced INTEGER DEFAULT 0,
    improvement_verified BOOLEAN,
    verification_notes TEXT,
    
    -- Temporal metadata
    provided_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMPTZ,
    integrated_at TIMESTAMPTZ,
    
    CONSTRAINT feedback_type_check 
        CHECK (feedback_type IN ('correction', 'enhancement', 'validation', 'clarification')),
    CONSTRAINT agreement_level_check 
        CHECK (agreement_level IN ('strongly_agree', 'agree', 'neutral', 'disagree', 'strongly_disagree')),
    CONSTRAINT feedback_status_check 
        CHECK (feedback_status IN ('pending', 'reviewed', 'integrated', 'rejected', 'obsolete'))
);

-- Create indexes for orchestration_feedback
CREATE INDEX IF NOT EXISTS idx_orchestration_feedback_decision_researcher ON orchestration_feedback(orchestration_decision_id, researcher_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_feedback_type_status ON orchestration_feedback(feedback_type, feedback_status);
CREATE INDEX IF NOT EXISTS idx_orchestration_feedback_provided_at ON orchestration_feedback(provided_at);


-- Create learning_patterns table
CREATE TABLE IF NOT EXISTS learning_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Pattern metadata
    pattern_name VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    context_signature VARCHAR(200) NOT NULL,
    
    -- Pattern definition
    conditions JSONB NOT NULL,
    recommendations JSONB NOT NULL,
    confidence DECIMAL(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Source tracking
    derived_from_feedback UUID REFERENCES orchestration_feedback(id),
    researcher_authority JSONB,
    
    -- Usage tracking
    times_applied INTEGER DEFAULT 0,
    success_rate DECIMAL(4,3) CHECK (success_rate >= 0 AND success_rate <= 1),
    last_applied TIMESTAMPTZ,
    
    -- Pattern evolution
    pattern_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pattern_type_check 
        CHECK (pattern_type IN ('avoidance', 'preference', 'enhancement', 'domain_specific')),
    CONSTRAINT pattern_status_check 
        CHECK (pattern_status IN ('active', 'deprecated', 'under_review', 'experimental'))
);

-- Create indexes for learning_patterns
CREATE INDEX IF NOT EXISTS idx_learning_patterns_context_type ON learning_patterns(context_signature, pattern_type);
CREATE INDEX IF NOT EXISTS idx_learning_patterns_status ON learning_patterns(pattern_status);
CREATE INDEX IF NOT EXISTS idx_learning_patterns_success_rate ON learning_patterns(success_rate DESC);


-- Create orchestration_overrides table
CREATE TABLE IF NOT EXISTS orchestration_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Reference to decision being overridden
    orchestration_decision_id UUID NOT NULL REFERENCES orchestration_decisions(id) ON DELETE CASCADE,
    
    -- Researcher applying override
    researcher_id INTEGER NOT NULL REFERENCES users(id),
    
    -- Override details
    override_type VARCHAR(50) NOT NULL,
    original_decision JSONB NOT NULL,
    overridden_decision JSONB NOT NULL,
    
    -- Justification
    justification TEXT NOT NULL,
    expert_knowledge_applied JSONB,
    
    -- Execution tracking
    override_applied BOOLEAN DEFAULT FALSE,
    execution_results JSONB,
    performance_comparison JSONB,
    
    -- Temporal metadata
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT override_type_check 
        CHECK (override_type IN ('full_replacement', 'tool_addition', 'tool_removal', 'model_change', 'strategy_change'))
);

-- Create indexes for orchestration_overrides
CREATE INDEX IF NOT EXISTS idx_orchestration_overrides_decision_researcher ON orchestration_overrides(orchestration_decision_id, researcher_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_overrides_applied_at ON orchestration_overrides(applied_at);


-- Add comments for documentation
COMMENT ON TABLE orchestration_feedback IS 'Researcher feedback on orchestration decisions for continuous improvement';
COMMENT ON TABLE learning_patterns IS 'Codified learning patterns derived from researcher feedback';
COMMENT ON TABLE orchestration_overrides IS 'Manual overrides applied by researchers to specific orchestration decisions';

COMMENT ON COLUMN orchestration_feedback.domain_specific_factors IS 'Domain knowledge that LLM missed in original decision';
COMMENT ON COLUMN orchestration_feedback.researcher_expertise IS 'Researcher expertise profile for weighting feedback authority';
COMMENT ON COLUMN learning_patterns.context_signature IS 'Signature for matching similar decision contexts';
COMMENT ON COLUMN learning_patterns.researcher_authority IS 'Authority assessment of source researcher for weighting';

COMMIT;

-- Verify tables were created
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('orchestration_feedback', 'learning_patterns', 'orchestration_overrides')
ORDER BY tablename;