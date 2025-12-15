-- ============================================
-- Migration: Add Authentication System
-- ============================================
-- Adds permissions column to users table and creates auth_tokens table

-- Add permissions column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT[] DEFAULT ARRAY[]::TEXT[];

-- Create auth_tokens table
CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    username VARCHAR(255) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    usage_count INTEGER DEFAULT 0,
    max_usage INTEGER DEFAULT 1000,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for auth_tokens
CREATE INDEX IF NOT EXISTS idx_auth_tokens_username ON auth_tokens(username);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON auth_tokens(expires_at);

-- Update default admin user with permissions if it exists
UPDATE users 
SET permissions = ARRAY['admin', 'upload', 'search', 'download']
WHERE username = 'ece30861defaultadminuser' 
  AND (permissions IS NULL OR array_length(permissions, 1) IS NULL);

COMMIT;
