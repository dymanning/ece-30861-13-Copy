-- ============================================
-- ECE 461 Phase 2 - Artifact Registry Schema
-- ============================================

-- Drop existing tables if they exist (for fresh setup)
DROP TABLE IF EXISTS monitoring_history CASCADE;
DROP TABLE IF EXISTS monitoring_config CASCADE;
DROP TABLE IF EXISTS artifacts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- Main Artifacts Table
-- ============================================
CREATE TABLE artifacts (
    -- Primary identifier
    id SERIAL PRIMARY KEY,
    
    -- Artifact metadata
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('model', 'dataset', 'code')),
    
    -- S3/storage URI and size information
    uri TEXT,
    size INTEGER DEFAULT 0,
    
    -- Source URL for artifact
    url TEXT NOT NULL,
    
    -- README content for regex search (CRITICAL for search functionality)
    readme TEXT,
    
    -- Flexible storage for additional metadata
    metadata JSONB DEFAULT '{}',
    
    -- Phase 1 Metrics - Quality Ratings
    rating JSONB DEFAULT '{
        "quality": 0,
        "size_score": {
            "raspberry_pi": 0,
            "jetson_nano": 0
        },
        "code_quality": 0,
        "dataset_quality": 0,
        "performance_claims": 0,
        "bus_factor": 0,
        "ramp_up_time": 0,
        "dataset_and_code_score": 0
    }',
    
    -- Cost metrics (in cents)
    cost JSONB DEFAULT '{
        "inference_cents": 0,
        "storage_cents": 0
    }',
    
    -- Dependencies/requirements
    dependencies TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Security monitoring fields
    is_sensitive BOOLEAN DEFAULT FALSE,
    monitoring_script VARCHAR(255) DEFAULT 'default-check.js',
    require_approval BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- Users Table (for authentication)
-- ============================================
CREATE TABLE users (
    username VARCHAR(255) PRIMARY KEY,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default admin user per spec requirements
-- Username: ece30861defaultadminuser
-- Password: correcthorsebatterystaple123(!__+@**(A;DROP TABLE artifacts
-- Note: In production, hash this password properly. For now, using placeholder.
INSERT INTO users (username, password_hash, is_admin) VALUES (
    'ece30861defaultadminuser',
    'placeholder_hash_replace_with_actual_hash',
    TRUE
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- Single-column indexes for basic queries
CREATE INDEX idx_artifacts_name ON artifacts(name);
CREATE INDEX idx_artifacts_type ON artifacts(type);

-- Composite index for filtered enumeration queries
CREATE INDEX idx_artifacts_name_type ON artifacts(name, type);

-- Index for pagination (ordered by creation time)
CREATE INDEX idx_artifacts_created_at ON artifacts(created_at DESC);

-- Full-text search index (GIN) for regex search
-- Combines name + README for comprehensive text search
CREATE INDEX idx_artifacts_fulltext 
    ON artifacts 
    USING GIN (
        to_tsvector('english', 
            COALESCE(name, '') || ' ' || COALESCE(readme, '')
        )
    );

-- ============================================
-- Triggers for updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_artifacts_updated_at
    BEFORE UPDATE ON artifacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Helper Functions
-- ============================================

-- Function to safely count total artifacts (with limit check for DoS prevention)
CREATE OR REPLACE FUNCTION count_artifacts_safe(max_count INTEGER DEFAULT 10000)
RETURNS INTEGER AS $$
DECLARE
    total INTEGER;
BEGIN
    SELECT COUNT(*) INTO total FROM artifacts;
    IF total > max_count THEN
        RETURN max_count + 1; -- Indicate exceeded
    END IF;
    RETURN total;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Monitoring History Table
-- ============================================
CREATE TABLE monitoring_history (
    id SERIAL PRIMARY KEY,
    artifact_id VARCHAR(50) NOT NULL,
    
    -- Execution details
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    script_name VARCHAR(255) NOT NULL,
    execution_duration_ms INTEGER NOT NULL,
    
    -- User context
    user_id VARCHAR(255),
    user_is_admin BOOLEAN DEFAULT FALSE,
    
    -- Results
    exit_code INTEGER NOT NULL,
    stdout TEXT,
    stderr TEXT,
    
    -- Decision outcome
    action_taken VARCHAR(20) NOT NULL CHECK (
        action_taken IN ('allowed', 'blocked', 'warned', 'error')
    ),
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_exit_code CHECK (exit_code >= 0 AND exit_code <= 255),
    CONSTRAINT fk_artifact FOREIGN KEY (artifact_id) 
        REFERENCES artifacts(id) ON DELETE CASCADE
);

-- Indexes for monitoring history
CREATE INDEX idx_monitoring_artifact ON monitoring_history(artifact_id);
CREATE INDEX idx_monitoring_executed_at ON monitoring_history(executed_at DESC);
CREATE INDEX idx_monitoring_action ON monitoring_history(action_taken);
CREATE INDEX idx_monitoring_user ON monitoring_history(user_id);
CREATE INDEX idx_monitoring_exit_code ON monitoring_history(exit_code);

-- Index for sensitive artifacts
CREATE INDEX idx_artifacts_sensitive ON artifacts(is_sensitive) 
WHERE is_sensitive = TRUE;

-- ============================================
-- Monitoring Configuration Table
-- ============================================
CREATE TABLE monitoring_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default monitoring configuration
INSERT INTO monitoring_config (key, value, description) VALUES
('default_script', 'default-check.js', 'Default monitoring script'),
('script_timeout_ms', '5000', 'Maximum script execution time in milliseconds'),
('block_on_nonzero', 'true', 'Block download if exit code is non-zero'),
('log_stdout', 'true', 'Log stdout from scripts'),
('log_stderr', 'true', 'Log stderr from scripts'),
('max_output_length', '10000', 'Maximum length of stdout/stderr to store');

-- ============================================
-- Sample Data (Optional - for testing)
-- ============================================

-- Uncomment below to insert sample artifacts for testing

/*
INSERT INTO artifacts (id, name, type, url, readme) VALUES
(
    '3847247294',
    'audience-classifier',
    'model',
    'https://huggingface.co/parvk11/audience_classifier_model',
    '# Audience Classifier\n\nThis model classifies text into different audience categories.\n\n## License\nMIT License'
),
(
    '5738291045',
    'bookcorpus',
    'dataset',
    'https://huggingface.co/datasets/bookcorpus',
    '# BookCorpus Dataset\n\nA large corpus of books for language model training.\n\n## License\nApache 2.0'
),
(
    '9182736455',
    'google-research-bert',
    'code',
    'https://github.com/google-research/bert',
    '# BERT: Pre-training of Deep Bidirectional Transformers\n\nOfficial implementation of BERT.\n\n## License\nApache 2.0'
);
*/
