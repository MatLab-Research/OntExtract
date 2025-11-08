-- Migration: Create app_settings table
-- Date: November 8, 2025
-- Description: Centralized application settings with category-based organization

CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB NOT NULL,
    category VARCHAR(50) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    description TEXT,
    default_value JSONB,
    requires_llm BOOLEAN DEFAULT FALSE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_app_settings_key ON app_settings(setting_key);
CREATE INDEX idx_app_settings_category ON app_settings(category);
CREATE INDEX idx_app_settings_user_id ON app_settings(user_id);

-- Comments
COMMENT ON TABLE app_settings IS 'Application settings with support for system-wide and user-specific configurations';
COMMENT ON COLUMN app_settings.setting_key IS 'Unique setting identifier (e.g., spacy_model)';
COMMENT ON COLUMN app_settings.setting_value IS 'Setting value stored as JSON';
COMMENT ON COLUMN app_settings.category IS 'Setting category: prompts, nlp, processing, llm, ui';
COMMENT ON COLUMN app_settings.data_type IS 'Data type hint: string, integer, boolean, json';
COMMENT ON COLUMN app_settings.user_id IS 'User ID for user-specific settings, NULL for system-wide';
