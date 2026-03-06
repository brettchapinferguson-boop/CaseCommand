-- Agent Outputs Table
-- Run this in: Supabase Dashboard > SQL Editor > New query
-- This table stores outputs from the nightly AI agent team

CREATE TABLE IF NOT EXISTS agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    output_type TEXT NOT NULL DEFAULT 'suggestion',  -- suggestion, code_fix, analysis, knowledge
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, applied, dismissed
    priority TEXT DEFAULT 'normal',  -- low, normal, high, critical
    run_id TEXT,  -- groups outputs from the same nightly run
    created_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ,
    applied_by TEXT
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_agent_outputs_status ON agent_outputs(status);
CREATE INDEX IF NOT EXISTS idx_agent_outputs_agent ON agent_outputs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_outputs_created ON agent_outputs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_outputs_run ON agent_outputs(run_id);

-- Allow service role full access (used by GitHub Actions runner)
ALTER TABLE agent_outputs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to agent_outputs"
    ON agent_outputs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Grant access to authenticated users (read-only for the admin dashboard)
CREATE POLICY "Authenticated users can view agent_outputs"
    ON agent_outputs
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can update agent_outputs status"
    ON agent_outputs
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);
