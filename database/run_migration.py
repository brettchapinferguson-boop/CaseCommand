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
    }
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
