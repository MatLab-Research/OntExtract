-- Add experiments table and relationship table
CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    experiment_type VARCHAR(50) NOT NULL,
    configuration TEXT,
    status VARCHAR(20) DEFAULT 'draft' NOT NULL,
    results TEXT,
    results_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    user_id INTEGER NOT NULL REFERENCES users(id)
);

-- Create association table for many-to-many relationship between experiments and documents
CREATE TABLE IF NOT EXISTS experiment_documents (
    experiment_id INTEGER REFERENCES experiments(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (experiment_id, document_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_experiments_user_id ON experiments(user_id);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_type ON experiments(experiment_type);
