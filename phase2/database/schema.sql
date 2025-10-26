-- ============================================
-- ECE 461 Phase 2 - Artifact Registry Schema
-- ============================================

-- Drop existing tables if they exist (for fresh setup)
DROP TABLE IF EXISTS artifacts CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- Main Artifacts Table
-- ============================================
CREATE TABLE artifacts (
    -- Primary identifier (OpenAPI: ArtifactID pattern '^[a-zA-Z0-9\-]+$')
    id VARCHAR(50) PRIMARY KEY,
    
    -- Artifact metadata
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('model', 'dataset', 'code')),
    
    -- Source URL for artifact
    url TEXT NOT NULL,
    
    -- README content for regex search (CRITICAL for search functionality)
    readme TEXT,
    
    -- Flexible storage for ratings, lineage, etc.
    metadata JSONB DEFAULT '{}',
    
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
