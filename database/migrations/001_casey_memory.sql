-- Migration: Add casey_memory table for persistent long-term memory
-- Run this in: https://supabase.com/dashboard/project/YOUR_PROJECT_ID/sql/new

CREATE TABLE IF NOT EXISTS casey_memory (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'note',   -- preference, pattern, fact, skill, note
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optional: create an index for category-based lookups
CREATE INDEX IF NOT EXISTS idx_casey_memory_category ON casey_memory(category);
CREATE INDEX IF NOT EXISTS idx_casey_memory_updated ON casey_memory(updated_at DESC);

-- Ensure the conversation_messages table exists (add if missing)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'web',
    sender_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_session
    ON conversation_messages(session_id, created_at);
