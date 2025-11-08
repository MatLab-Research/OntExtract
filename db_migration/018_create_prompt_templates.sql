-- Migration: Create prompt_templates table
-- Date: November 8, 2025
-- Description: Jinja2 prompt templates for dual-path workflow (template-only vs LLM-enhanced)

CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    template_key VARCHAR(100) UNIQUE NOT NULL,
    template_text TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    variables JSONB NOT NULL DEFAULT '{}',
    supports_llm_enhancement BOOLEAN DEFAULT TRUE,
    llm_enhancement_prompt TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_prompt_templates_key ON prompt_templates(template_key);
CREATE INDEX idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX idx_prompt_templates_active ON prompt_templates(is_active);

-- Comments
COMMENT ON TABLE prompt_templates IS 'Jinja2 templates for generating descriptions and prompts with optional LLM enhancement';
COMMENT ON COLUMN prompt_templates.template_key IS 'Unique template identifier (e.g., experiment_description_single_document)';
COMMENT ON COLUMN prompt_templates.template_text IS 'Jinja2 template text with {{ variable }} syntax';
COMMENT ON COLUMN prompt_templates.category IS 'Template category: experiment_description, analysis_summary, etc.';
COMMENT ON COLUMN prompt_templates.variables IS 'Required variables with types: {"document_title": "string", "word_count": "int"}';
COMMENT ON COLUMN prompt_templates.supports_llm_enhancement IS 'Whether this template can be enhanced by LLM';
COMMENT ON COLUMN prompt_templates.llm_enhancement_prompt IS 'Prompt for LLM to enhance the rendered template output';
COMMENT ON COLUMN prompt_templates.is_active IS 'Whether template is currently active/enabled';
