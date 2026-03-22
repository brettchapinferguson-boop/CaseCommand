#!/usr/bin/env python3
"""
Run CaseCommand database migrations against Supabase.
Usage: python3 run_migration.py
Requires: pip install httpx
"""
import sys
import httpx

PROJECT_REF = "alkkwmrbcclgoxlawigb"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFsa2t3bXJiY2NsZ294bGF3aWdiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTUzNDYwMiwiZXhwIjoyMDg3MTEwNjAyfQ.bvNhEuGPnvpnxMYd8mb26w_sPK94r41UduBrUP06pd0"

MIGRATIONS = [
    {
        "name": "001_casey_memory",
        "sql": """
CREATE TABLE IF NOT EXISTS casey_memory (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'note',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_casey_memory_category ON casey_memory(category);
CREATE INDEX IF NOT EXISTS idx_casey_memory_updated ON casey_memory(updated_at DESC);

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
""",
    },
    {
        "name": "002_fix_rls_policies",
        "sql": """
-- Drop restrictive user-only policies that block the service-role server
DROP POLICY IF EXISTS "Users can view their own cases" ON cases;
DROP POLICY IF EXISTS "Users can create their own cases" ON cases;
DROP POLICY IF EXISTS "Users can update their own cases" ON cases;
DROP POLICY IF EXISTS "Users can delete their own cases" ON cases;
DROP POLICY IF EXISTS "Users can view their own discovery analyses" ON discovery_analyses;
DROP POLICY IF EXISTS "Users can create discovery analyses" ON discovery_analyses;
DROP POLICY IF EXISTS "Users can view their own examination outlines" ON examination_outlines;
DROP POLICY IF EXISTS "Users can create examination outlines" ON examination_outlines;
DROP POLICY IF EXISTS "Users can view their own settlement narratives" ON settlement_narratives;
DROP POLICY IF EXISTS "Users can create settlement narratives" ON settlement_narratives;

-- Replace with open policies (server handles auth at the API layer via AUTH_TOKEN)
CREATE POLICY "Service role has full access to cases"
    ON cases FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role has full access to discovery_analyses"
    ON discovery_analyses FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role has full access to examination_outlines"
    ON examination_outlines FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role has full access to settlement_narratives"
    ON settlement_narratives FOR ALL USING (true) WITH CHECK (true);

-- Make user_id optional (nullable) since the server doesn't authenticate via Supabase auth
ALTER TABLE cases ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE discovery_analyses ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE examination_outlines ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE settlement_narratives ALTER COLUMN user_id DROP NOT NULL;
""",
    },
]


def run_migrations():
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    for migration in MIGRATIONS:
        print(f"Running migration: {migration['name']}...")
        resp = httpx.post(
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
            headers={"Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"},
            json={"query": migration["sql"]},
            timeout=30,
        )
        if resp.status_code == 200:
            print(f"  ✅ {migration['name']} — done")
        else:
            print(f"  ❌ {migration['name']} failed: {resp.status_code} {resp.text[:200]}")
            print("\nFallback: trying via REST API rpc...")
            # Try via PostgREST rpc as fallback
            resp2 = httpx.post(
                f"https://{PROJECT_REF}.supabase.co/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"sql": migration["sql"]},
                timeout=30,
            )
            if resp2.status_code in (200, 204):
                print(f"  ✅ {migration['name']} via rpc — done")
            else:
                print(f"  ❌ rpc also failed: {resp2.status_code}")
                print("\n--- MANUAL FALLBACK ---")
                print("Run this SQL in: https://supabase.com/dashboard/project/alkkwmrbcclgoxlawigb/sql/new")
                print(migration["sql"])
                sys.exit(1)

    print("\n✅ All migrations complete.")


if __name__ == "__main__":
    run_migrations()
