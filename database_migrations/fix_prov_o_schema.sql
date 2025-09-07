-- Fix PROV-O schema to match the models exactly

-- Update prov_agents table to match ProvAgent model
ALTER TABLE prov_agents 
  DROP COLUMN IF EXISTS agent_name CASCADE,
  DROP COLUMN IF EXISTS agent_description CASCADE,
  DROP COLUMN IF EXISTS agent_version CASCADE;

ALTER TABLE prov_agents 
  ADD COLUMN IF NOT EXISTS agent_identifier VARCHAR(255) UNIQUE NOT NULL DEFAULT 'default';

-- Remove the old constraint and add the correct one
ALTER TABLE prov_agents 
  DROP CONSTRAINT IF EXISTS valid_agent_name;

ALTER TABLE prov_agents 
  ADD CONSTRAINT valid_agent_type CHECK (agent_type IN ('human', 'llm', 'tool', 'system'));

-- Clear existing agents and add the correct ones
TRUNCATE TABLE prov_agents CASCADE;

-- Insert agents with correct schema
INSERT INTO prov_agents (agent_type, agent_identifier, agent_metadata) VALUES 
  ('tool', 'langextract_gemini', '{"provider": "google", "model": "gemini-2.0-flash-exp", "version": "1.0.9"}'),
  ('system', 'ontextract_system', '{"features": ["JCDL", "period_aware", "human_in_loop"], "version": "1.0.0"}'),
  ('system', 'llm_orchestrator', '{"capabilities": ["tool_routing", "synthesis", "quality_control"], "version": "1.0.0"}');

-- Check if we need to update other tables to match their models
-- Let me check what columns the other models expect
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name IN ('prov_agents', 'prov_activities', 'prov_entities', 'prov_relationships')
ORDER BY table_name, ordinal_position;