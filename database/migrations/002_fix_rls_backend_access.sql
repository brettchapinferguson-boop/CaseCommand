-- Migration 002: Fix RLS policies for backend server access
-- ============================================================
-- PROBLEM:
--   The backend server (server.py) uses a service-role key to connect to
--   Supabase.  The original RLS policies require `auth.uid() = user_id`,
--   but the server has no user session context — it is a server-side key.
--
--   Result:
--     • Case INSERT from backend fails with RLS violation → 500 error
--     • Case SELECT from backend returns 0 rows → Casey sees "no cases"
--
-- SOLUTION:
--   This is a single-user law-firm app.  Security is enforced by the
--   AUTH_TOKEN on the FastAPI server, not by per-user Supabase RLS.
--
--   We replace the strict user-scoped policies with policies that:
--     1. Allow the service-role key (used by the server) full access.
--     2. Allow the authenticated user (used by the React frontend) to
--        read and manage cases where user_id matches their UUID OR where
--        user_id is NULL (cases created by the server with no user context).
--
-- HOW TO RUN:
--   Supabase Dashboard → SQL Editor → paste & run this file.
-- ============================================================

-- ── cases ───────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view their own cases"      ON cases;
DROP POLICY IF EXISTS "Users can create their own cases"    ON cases;
DROP POLICY IF EXISTS "Users can update their own cases"    ON cases;
DROP POLICY IF EXISTS "Users can delete their own cases"    ON cases;

-- Allow read: user owns the case OR case was created by the server (user_id IS NULL)
CREATE POLICY "Read own cases or server cases"
    ON cases FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL);

-- Allow insert: user sets their own user_id, OR server inserts with NULL user_id
CREATE POLICY "Insert own cases or server cases"
    ON cases FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.uid() IS NULL);

-- Allow update: same scope as read
CREATE POLICY "Update own cases or server cases"
    ON cases FOR UPDATE
    USING (auth.uid() = user_id OR user_id IS NULL);

-- Allow delete: same scope as read
CREATE POLICY "Delete own cases or server cases"
    ON cases FOR DELETE
    USING (auth.uid() = user_id OR user_id IS NULL);


-- ── discovery_analyses ──────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view their own discovery analyses"  ON discovery_analyses;
DROP POLICY IF EXISTS "Users can create discovery analyses"          ON discovery_analyses;

CREATE POLICY "Read own or server discovery analyses"
    ON discovery_analyses FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Insert own or server discovery analyses"
    ON discovery_analyses FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.uid() IS NULL);


-- ── examination_outlines ────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view their own examination outlines"  ON examination_outlines;
DROP POLICY IF EXISTS "Users can create examination outlines"          ON examination_outlines;

CREATE POLICY "Read own or server examination outlines"
    ON examination_outlines FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Insert own or server examination outlines"
    ON examination_outlines FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.uid() IS NULL);


-- ── settlement_narratives ───────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view their own settlement narratives"  ON settlement_narratives;
DROP POLICY IF EXISTS "Users can create settlement narratives"          ON settlement_narratives;

CREATE POLICY "Read own or server settlement narratives"
    ON settlement_narratives FOR SELECT
    USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Insert own or server settlement narratives"
    ON settlement_narratives FOR INSERT
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL OR auth.uid() IS NULL);


-- ── conversation_messages (no RLS yet — enable and add open policy) ─────────

ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to conversation messages"
    ON conversation_messages FOR ALL
    USING (true)
    WITH CHECK (true);


-- ── casey_memory (no RLS yet — enable and add open policy) ──────────────────

ALTER TABLE casey_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to casey memory"
    ON casey_memory FOR ALL
    USING (true)
    WITH CHECK (true);
