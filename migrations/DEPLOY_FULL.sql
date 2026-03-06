-- CaseCommand Database Schema
-- Run this in: https://supabase.com/dashboard/project/YOUR_PROJECT_ID/sql/new
-- Expected result: "Success. No rows returned"

-- ============================================================
-- TABLES
-- ============================================================

-- Cases: core case records
CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    case_name TEXT NOT NULL,
    case_number TEXT,
    client_name TEXT,
    opposing_party TEXT,
    case_type TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Discovery analyses: AI-generated analysis results
CREATE TABLE IF NOT EXISTS discovery_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    discovery_type TEXT NOT NULL,
    requests_and_responses JSONB,
    analysis_result TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Examination outlines: AI-generated direct/cross examination outlines
CREATE TABLE IF NOT EXISTS examination_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    witness_name TEXT NOT NULL,
    witness_role TEXT,
    exam_type TEXT,
    case_theory TEXT,
    case_documents JSONB,
    outline_result TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Settlement narratives: AI-generated settlement assessments
CREATE TABLE IF NOT EXISTS settlement_narratives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    trigger_point TEXT,
    valuation_data JSONB,
    recommendation_data JSONB,
    narrative_result TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE examination_outlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlement_narratives ENABLE ROW LEVEL SECURITY;

-- Cases policies
CREATE POLICY "Users can view their own cases"
    ON cases FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own cases"
    ON cases FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own cases"
    ON cases FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own cases"
    ON cases FOR DELETE USING (auth.uid() = user_id);

-- Discovery analyses policies
CREATE POLICY "Users can view their own discovery analyses"
    ON discovery_analyses FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create discovery analyses"
    ON discovery_analyses FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Examination outlines policies
CREATE POLICY "Users can view their own examination outlines"
    ON examination_outlines FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create examination outlines"
    ON examination_outlines FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Settlement narratives policies
CREATE POLICY "Users can view their own settlement narratives"
    ON settlement_narratives FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create settlement narratives"
    ON settlement_narratives FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Conversation messages: persisted chat history across all channels
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'web',  -- web, telegram, sms, whatsapp
    sender_id TEXT,                        -- Telegram user_id, phone number, etc.
    role TEXT NOT NULL,                     -- user, assistant
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',           -- tool calls, document info, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_session
    ON conversation_messages(session_id, created_at);

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_cases_updated_at
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- CaseCommand — Multi-Tenant Schema Migration
-- Run this AFTER schema.sql and agent_outputs_schema.sql
-- Adds organizations, firm config, org membership, and usage tracking

-- ============================================================
-- ORGANIZATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID REFERENCES auth.users(id),
    subscription_tier TEXT NOT NULL DEFAULT 'solo',  -- solo, firm, enterprise
    subscription_status TEXT NOT NULL DEFAULT 'trialing',  -- trialing, active, past_due, canceled
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_owner ON organizations(owner_id);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe ON organizations(stripe_customer_id);

-- ============================================================
-- ORGANIZATION MEMBERS
-- ============================================================

CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'user',  -- owner, admin, attorney, paralegal, readonly
    invited_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON org_members(org_id);

-- ============================================================
-- FIRM CONFIGURATION (per-org customization)
-- ============================================================

CREATE TABLE IF NOT EXISTS firm_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,
    firm_name TEXT NOT NULL DEFAULT '',
    attorney_name TEXT DEFAULT '',
    bar_number TEXT DEFAULT '',
    jurisdiction TEXT DEFAULT 'California',
    firm_address TEXT DEFAULT '',
    firm_phone TEXT DEFAULT '',
    court_formatting TEXT DEFAULT '',  -- custom formatting preferences
    logo_url TEXT DEFAULT '',
    custom_soul TEXT DEFAULT '',  -- override SOUL.md per firm (enterprise only)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_firm_config_org ON firm_config(org_id);

-- ============================================================
-- USAGE TRACKING (per-org, per-period)
-- ============================================================

CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    period TEXT NOT NULL,  -- YYYY-MM format
    ai_calls INTEGER NOT NULL DEFAULT 0,
    tokens_used BIGINT NOT NULL DEFAULT 0,
    documents_generated INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, period)
);

CREATE INDEX IF NOT EXISTS idx_usage_tracking_org_period ON usage_tracking(org_id, period);

-- Function to increment usage counters
CREATE OR REPLACE FUNCTION increment_usage(
    p_org_id UUID,
    p_period TEXT,
    p_ai_calls INTEGER DEFAULT 1,
    p_tokens INTEGER DEFAULT 0,
    p_docs INTEGER DEFAULT 0
) RETURNS void AS $$
BEGIN
    INSERT INTO usage_tracking (org_id, period, ai_calls, tokens_used, documents_generated)
    VALUES (p_org_id, p_period, p_ai_calls, p_tokens, p_docs)
    ON CONFLICT (org_id, period)
    DO UPDATE SET
        ai_calls = usage_tracking.ai_calls + p_ai_calls,
        tokens_used = usage_tracking.tokens_used + p_tokens,
        documents_generated = usage_tracking.documents_generated + p_docs,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- ADD org_id TO EXISTING TABLES
-- ============================================================

-- Cases
ALTER TABLE cases ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_cases_org ON cases(org_id);

-- Discovery analyses
ALTER TABLE discovery_analyses ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Examination outlines
ALTER TABLE examination_outlines ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Settlement narratives
ALTER TABLE settlement_narratives ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);

-- Conversation messages
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);
CREATE INDEX IF NOT EXISTS idx_conversation_org ON conversation_messages(org_id);

-- ============================================================
-- ROW LEVEL SECURITY — Multi-tenant policies
-- ============================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE firm_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- Organizations: members can view their own org
CREATE POLICY "Users can view their organization"
    ON organizations FOR SELECT
    USING (
        id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- Org members: users can see fellow members
CREATE POLICY "Users can view org members"
    ON org_members FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- Firm config: org members can view their firm config
CREATE POLICY "Users can view their firm config"
    ON firm_config FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- Firm config: only admins/owners can update
CREATE POLICY "Admins can update firm config"
    ON firm_config FOR UPDATE
    USING (
        org_id IN (
            SELECT org_id FROM org_members
            WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
        )
    );

-- Usage tracking: org members can view
CREATE POLICY "Users can view their usage"
    ON usage_tracking FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

-- Update cases policies for multi-tenant
CREATE POLICY "Users can view their org cases"
    ON cases FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
        OR (org_id IS NULL AND auth.uid() = user_id)
    );

-- Service role full access (for backend operations)
CREATE POLICY "Service role full access to organizations"
    ON organizations FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to org_members"
    ON org_members FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to firm_config"
    ON firm_config FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access to usage_tracking"
    ON usage_tracking FOR ALL USING (true) WITH CHECK (true);

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_firm_config_updated_at
    BEFORE UPDATE ON firm_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
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
-- ============================================================
-- Migration 001: RAG Pipeline & Background Jobs
-- CaseCommand — Legal AI SaaS
--
-- Adds: uploaded_files, document_chunks (with pgvector), background_jobs
-- Depends on: schema.sql, 002_multi_tenant.sql (organizations, org_members)
-- ============================================================

-- Enable pgvector for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- HELPER: updated_at trigger function
-- (idempotent — may already exist from schema.sql)
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TABLE: uploaded_files
-- Tracks every file uploaded by users, linked to an org and
-- optionally to a specific case.
-- ============================================================

CREATE TABLE IF NOT EXISTS uploaded_files (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    case_id         UUID                 REFERENCES cases(id) ON DELETE SET NULL,
    filename        TEXT        NOT NULL,
    original_filename TEXT      NOT NULL,
    file_type       TEXT        NOT NULL,           -- e.g. 'pdf', 'docx', 'image'
    file_size_bytes BIGINT      NOT NULL,
    storage_path    TEXT        NOT NULL,            -- path within Supabase Storage bucket
    mime_type       TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'uploaded',  -- uploaded | processing | ready | error
    metadata        JSONB       DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  uploaded_files IS 'Files uploaded by users for RAG ingestion and document generation.';
COMMENT ON COLUMN uploaded_files.status IS 'Lifecycle: uploaded -> processing -> ready | error';
COMMENT ON COLUMN uploaded_files.storage_path IS 'Relative path inside the case-files Storage bucket.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_uploaded_files_org    ON uploaded_files(org_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_user   ON uploaded_files(user_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_case   ON uploaded_files(case_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(status);

-- updated_at trigger
CREATE TRIGGER update_uploaded_files_updated_at
    BEFORE UPDATE ON uploaded_files
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE: document_chunks
-- Text chunks extracted from uploaded files, with vector
-- embeddings for semantic search (RAG retrieval).
-- ============================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id     UUID        NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chunk_index INTEGER     NOT NULL,
    content     TEXT        NOT NULL,
    token_count INTEGER,
    page_number INTEGER,                            -- nullable; page the chunk originated from
    metadata    JSONB       DEFAULT '{}',
    embedding   vector(1024),                       -- pgvector column for semantic search
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  document_chunks IS 'Text chunks with embeddings extracted from uploaded_files for RAG retrieval.';
COMMENT ON COLUMN document_chunks.embedding IS '1024-dim vector from embedding model (e.g. text-embedding-3-large).';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_file   ON document_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_org    ON document_chunks(org_id);

-- Unique constraint: one chunk_index per file
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_chunks_file_chunk
    ON document_chunks(file_id, chunk_index);

-- HNSW index for fast approximate nearest-neighbor vector search
-- Using cosine distance (<=>) which is standard for normalized embeddings
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- TABLE: background_jobs
-- Lightweight async task queue for file processing,
-- embedding generation, document generation, etc.
-- ============================================================

CREATE TABLE IF NOT EXISTS background_jobs (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id       UUID                 REFERENCES auth.users(id) ON DELETE SET NULL,
    job_type      TEXT        NOT NULL,              -- e.g. 'extract_text', 'generate_embeddings', 'generate_document'
    status        TEXT        NOT NULL DEFAULT 'pending',  -- pending | running | completed | failed
    payload       JSONB       NOT NULL DEFAULT '{}',
    result        JSONB,
    error_message TEXT,
    attempts      INTEGER     NOT NULL DEFAULT 0,
    max_attempts  INTEGER     NOT NULL DEFAULT 3,
    scheduled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  background_jobs IS 'Async job queue for file processing, embedding generation, and document generation.';
COMMENT ON COLUMN background_jobs.status IS 'Lifecycle: pending -> running -> completed | failed';
COMMENT ON COLUMN background_jobs.attempts IS 'Number of times this job has been attempted. Retries up to max_attempts.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_background_jobs_org      ON background_jobs(org_id);
CREATE INDEX IF NOT EXISTS idx_background_jobs_status   ON background_jobs(status);
CREATE INDEX IF NOT EXISTS idx_background_jobs_type     ON background_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_background_jobs_scheduled
    ON background_jobs(scheduled_at)
    WHERE status = 'pending';

-- ============================================================
-- ROW LEVEL SECURITY
-- All three tables are scoped to the user's organization
-- via org_members membership lookup.
-- ============================================================

ALTER TABLE uploaded_files   ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks  ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_jobs  ENABLE ROW LEVEL SECURITY;

-- Helper: reusable org membership check
-- auth.uid() must be a member of the row's org_id
-- (used inline below since Postgres RLS doesn't support function-based policies cleanly)

-- ----- uploaded_files -----

CREATE POLICY "Org members can view uploaded files"
    ON uploaded_files FOR SELECT
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can upload files"
    ON uploaded_files FOR INSERT
    WITH CHECK (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can update their uploaded files"
    ON uploaded_files FOR UPDATE
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can delete their uploaded files"
    ON uploaded_files FOR DELETE
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

-- Service role bypass for backend workers
CREATE POLICY "Service role full access to uploaded_files"
    ON uploaded_files FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ----- document_chunks -----

CREATE POLICY "Org members can view document chunks"
    ON document_chunks FOR SELECT
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can insert document chunks"
    ON document_chunks FOR INSERT
    WITH CHECK (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can delete document chunks"
    ON document_chunks FOR DELETE
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

-- Service role bypass for backend workers (embedding pipeline)
CREATE POLICY "Service role full access to document_chunks"
    ON document_chunks FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ----- background_jobs -----

CREATE POLICY "Org members can view their jobs"
    ON background_jobs FOR SELECT
    USING (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

CREATE POLICY "Org members can create jobs"
    ON background_jobs FOR INSERT
    WITH CHECK (
        org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid())
    );

-- Service role bypass for backend job runner
CREATE POLICY "Service role full access to background_jobs"
    ON background_jobs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- UTILITY: Vector similarity search function
-- Returns the most relevant chunks for a given embedding
-- within an organization, with optional case scoping.
-- ============================================================

CREATE OR REPLACE FUNCTION match_document_chunks(
    p_org_id     UUID,
    p_embedding  vector(1024),
    p_match_count INTEGER DEFAULT 10,
    p_case_id    UUID DEFAULT NULL
)
RETURNS TABLE (
    id          UUID,
    file_id     UUID,
    chunk_index INTEGER,
    content     TEXT,
    page_number INTEGER,
    metadata    JSONB,
    similarity  FLOAT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.file_id,
        dc.chunk_index,
        dc.content,
        dc.page_number,
        dc.metadata,
        1 - (dc.embedding <=> p_embedding) AS similarity
    FROM document_chunks dc
    JOIN uploaded_files uf ON uf.id = dc.file_id
    WHERE dc.org_id = p_org_id
      AND dc.embedding IS NOT NULL
      AND (p_case_id IS NULL OR uf.case_id = p_case_id)
    ORDER BY dc.embedding <=> p_embedding
    LIMIT p_match_count;
END;
$$;

COMMENT ON FUNCTION match_document_chunks IS 'Semantic search: returns top-k document chunks by cosine similarity within an org, optionally scoped to a case.';
-- ============================================================
-- Migration 002: Supabase Storage — case-files bucket & policies
-- CaseCommand — Legal AI SaaS
--
-- Creates the 'case-files' storage bucket and sets up
-- org-scoped access policies for authenticated users.
-- Depends on: 002_multi_tenant.sql (organizations, org_members)
-- ============================================================

-- ============================================================
-- BUCKET: case-files
-- Stores uploaded legal documents (PDFs, DOCX, images, etc.)
-- Files are organized as: {org_id}/{case_id|_general}/{filename}
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'case-files',
    'case-files',
    false,                          -- private bucket; access controlled via policies
    52428800,                       -- 50 MB max file size
    ARRAY[
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/plain',
        'text/csv',
        'image/png',
        'image/jpeg',
        'image/webp',
        'image/tiff'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- STORAGE POLICIES
-- All policies enforce org-scoped access: the first path segment
-- must be an org_id that the authenticated user belongs to.
--
-- Storage path convention: case-files/{org_id}/...
-- storage.foldername(name) returns an array of path segments.
-- ============================================================

-- SELECT — Org members can read/download files in their org folder
CREATE POLICY "Org members can read case files"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'case-files'
        AND (storage.foldername(name))[1]::uuid IN (
            SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
        )
    );

-- INSERT — Org members can upload files to their org folder
CREATE POLICY "Org members can upload case files"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'case-files'
        AND (storage.foldername(name))[1]::uuid IN (
            SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
        )
    );

-- UPDATE — Org members can update/overwrite files in their org folder
CREATE POLICY "Org members can update case files"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (
        bucket_id = 'case-files'
        AND (storage.foldername(name))[1]::uuid IN (
            SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
        )
    );

-- DELETE — Org members can delete files in their org folder
CREATE POLICY "Org members can delete case files"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'case-files'
        AND (storage.foldername(name))[1]::uuid IN (
            SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()
        )
    );

-- Service role bypass — backend workers need unrestricted access
-- (Supabase service_role already bypasses RLS, but explicit policy
-- is included for clarity and defense-in-depth.)
CREATE POLICY "Service role full access to case files"
    ON storage.objects FOR ALL
    TO service_role
    USING (bucket_id = 'case-files')
    WITH CHECK (bucket_id = 'case-files');
-- Migration 003: Create the match_documents RPC function for vector similarity search.
-- Requires the pgvector extension and the document_chunks table to exist.

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1024),
    match_org_id UUID,
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.7,
    filter_case_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    file_id UUID,
    case_id UUID,
    content TEXT,
    chunk_index INT,
    page_number INT,
    token_count INT,
    metadata JSONB,
    similarity FLOAT,
    file_name TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.file_id,
        df.case_id,
        dc.content,
        dc.chunk_index,
        dc.page_number,
        dc.token_count,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        df.file_name
    FROM document_chunks dc
    LEFT JOIN document_files df ON df.id = dc.file_id
    WHERE dc.org_id = match_org_id
      AND 1 - (dc.embedding <=> query_embedding) > match_threshold
      AND (filter_case_id IS NULL OR df.case_id = filter_case_id)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
-- ============================================================
-- Migration 004: Full Litigation Lifecycle Tables
-- CaseCommand — Comprehensive Legal AI Platform
--
-- Adds: client_intakes, intake_causes_of_action, prima_facie_elements,
--        discovery_sets, discovery_items, case_deadlines, case_calendar_events,
--        motions, contract_reviews, deposition_preps, verdict_library,
--        case_documents_index, case_facts, case_timeline
-- ============================================================

-- ============================================================
-- 1. CLIENT INTAKE SYSTEM
-- ============================================================

-- Core intake record — everything starts here
CREATE TABLE IF NOT EXISTS client_intakes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by      UUID        REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Client information
    client_first_name   TEXT    NOT NULL,
    client_last_name    TEXT    NOT NULL,
    client_email        TEXT,
    client_phone        TEXT,
    client_address      TEXT,
    client_dob          DATE,
    preferred_language  TEXT    DEFAULT 'English',

    -- Employment-specific fields
    employer_name       TEXT,
    employer_address    TEXT,
    job_title           TEXT,
    hire_date           DATE,
    termination_date    DATE,
    employment_status   TEXT,   -- current, terminated, resigned, constructive_discharge
    annual_salary       NUMERIC(12,2),
    supervisor_name     TEXT,
    hr_contact          TEXT,
    union_member        BOOLEAN DEFAULT false,

    -- Incident details
    incident_date       DATE,
    incident_description TEXT,
    protected_class     TEXT[], -- race, sex, age, disability, religion, national_origin, etc.
    adverse_actions     TEXT[], -- termination, demotion, harassment, retaliation, etc.
    witnesses           JSONB   DEFAULT '[]',
    prior_complaints    JSONB   DEFAULT '[]', -- internal HR complaints, DFEH/EEOC filings

    -- Administrative exhaustion
    dfeh_filed          BOOLEAN DEFAULT false,
    dfeh_filing_date    DATE,
    dfeh_case_number    TEXT,
    right_to_sue        BOOLEAN DEFAULT false,
    right_to_sue_date   DATE,
    eeoc_filed          BOOLEAN DEFAULT false,
    eeoc_case_number    TEXT,

    -- Case evaluation
    ai_summary          TEXT,
    ai_risk_assessment  JSONB   DEFAULT '{}',
    overall_score       NUMERIC(3,1),  -- 0.0 to 10.0 viability score
    recommended_action  TEXT,   -- accept, decline, needs_review, needs_documents

    -- Status workflow
    status              TEXT    NOT NULL DEFAULT 'new',
    -- new -> screening -> reviewed -> accepted -> case_created | declined
    case_id             UUID    REFERENCES cases(id) ON DELETE SET NULL,
    reviewed_by         UUID    REFERENCES auth.users(id) ON DELETE SET NULL,
    reviewed_at         TIMESTAMPTZ,
    decline_reason      TEXT,

    -- Conversation / voice transcript
    transcript          TEXT,
    recording_url       TEXT,

    -- Metadata
    source_channel      TEXT    DEFAULT 'web', -- web, phone, telegram, referral
    referral_source     TEXT,
    conflict_check      JSONB   DEFAULT '{}',
    metadata            JSONB   DEFAULT '{}',

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intakes_org ON client_intakes(org_id);
CREATE INDEX IF NOT EXISTS idx_intakes_status ON client_intakes(status);
CREATE INDEX IF NOT EXISTS idx_intakes_case ON client_intakes(case_id);

CREATE TRIGGER update_intakes_updated_at
    BEFORE UPDATE ON client_intakes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Causes of action identified for each intake
CREATE TABLE IF NOT EXISTS intake_causes_of_action (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_id       UUID        NOT NULL REFERENCES client_intakes(id) ON DELETE CASCADE,
    org_id          UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    cause_of_action TEXT        NOT NULL,
    -- e.g.: FEHA_discrimination, FEHA_harassment, FEHA_retaliation,
    --       wrongful_termination, failure_to_accommodate, failure_to_engage_interactive_process,
    --       CFRA_violation, wage_theft, breach_of_contract, IIED, negligent_supervision

    statute_code        TEXT,       -- e.g. Gov. Code 12940(a)
    statute_of_limitations_date DATE,
    sol_status          TEXT,       -- active, expiring_soon, expired
    viable              BOOLEAN DEFAULT true,
    confidence_score    NUMERIC(3,1),

    -- Prima facie element analysis stored as JSONB array
    -- Each element: {name, description, satisfied, supporting_facts, missing_facts}
    prima_facie_elements JSONB   NOT NULL DEFAULT '[]',

    -- Affirmative defenses that could kill the claim
    affirmative_defenses JSONB   DEFAULT '[]',
    -- Each: {defense, risk_level, notes}

    ai_analysis         TEXT,
    notes               TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coa_intake ON intake_causes_of_action(intake_id);

CREATE TRIGGER update_coa_updated_at
    BEFORE UPDATE ON intake_causes_of_action
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 2. CASE FACTS TABLE — Central fact repository
-- ============================================================

CREATE TABLE IF NOT EXISTS case_facts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    fact_text       TEXT    NOT NULL,
    fact_date       DATE,
    fact_type       TEXT,   -- testimony, document, admission, physical_evidence
    source          TEXT,   -- depo of X, exhibit Y, intake interview
    source_doc_id   UUID,   -- FK to uploaded_files if from a document
    relevance       TEXT[], -- which causes of action this fact supports
    disputed        BOOLEAN DEFAULT false,
    importance      TEXT    DEFAULT 'medium', -- low, medium, high, critical

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_facts_case ON case_facts(case_id);


-- ============================================================
-- 3. DISCOVERY SYSTEM
-- ============================================================

CREATE TABLE IF NOT EXISTS discovery_sets (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    set_type        TEXT    NOT NULL,
    -- form_interrogatories, special_interrogatories, rfp, rfa,
    -- deposition_notice, subpoena_duces_tecum, subpoena_testimony

    set_number      INTEGER NOT NULL DEFAULT 1,
    direction       TEXT    NOT NULL DEFAULT 'propounding', -- propounding | responding
    propounding_party TEXT,
    responding_party  TEXT,

    -- Dates
    served_date     DATE,
    due_date        DATE,
    extended_due_date DATE,
    response_received_date DATE,

    status          TEXT    DEFAULT 'draft',
    -- draft -> served -> response_due -> response_received -> analyzed | motion_filed

    meet_confer_date    DATE,
    meet_confer_status  TEXT,   -- not_needed, pending, completed, failed

    ai_generated    BOOLEAN DEFAULT false,
    ai_analysis     TEXT,
    metadata        JSONB   DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_discovery_case ON discovery_sets(case_id);

CREATE TRIGGER update_discovery_sets_updated_at
    BEFORE UPDATE ON discovery_sets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Individual discovery items within a set
CREATE TABLE IF NOT EXISTS discovery_items (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    set_id          UUID        NOT NULL REFERENCES discovery_sets(id) ON DELETE CASCADE,

    item_number     INTEGER     NOT NULL,
    request_text    TEXT        NOT NULL,
    response_text   TEXT,
    objections      TEXT,

    -- AI analysis of this specific item
    ai_analysis     TEXT,
    analysis_flags  TEXT[],     -- evasive, boilerplate_objection, admission, inconsistent
    follow_up_needed BOOLEAN    DEFAULT false,
    follow_up_text  TEXT,

    -- Link to facts this request targets
    targeted_facts  UUID[],     -- references case_facts.id
    targeted_elements TEXT[],   -- which prima facie elements

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_discovery_items_set ON discovery_items(set_id);


-- ============================================================
-- 4. CASE CALENDAR / DEADLINES
-- ============================================================

CREATE TABLE IF NOT EXISTS case_deadlines (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    title           TEXT    NOT NULL,
    description     TEXT,
    deadline_date   DATE    NOT NULL,
    deadline_time   TIME,
    deadline_type   TEXT    NOT NULL,
    -- filing, discovery, hearing, trial, statute_of_limitations,
    -- meet_confer, deposition, mediation, settlement_conference, other

    source          TEXT,   -- CCP section or rule generating this deadline
    auto_generated  BOOLEAN DEFAULT false,
    completed       BOOLEAN DEFAULT false,
    completed_at    TIMESTAMPTZ,

    -- Reminder settings
    reminder_days   INTEGER[] DEFAULT ARRAY[7, 3, 1],
    last_reminder   TIMESTAMPTZ,

    -- Priority
    priority        TEXT    DEFAULT 'normal', -- low, normal, high, critical
    color           TEXT,   -- hex color for calendar display

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deadlines_case ON case_deadlines(case_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_date ON case_deadlines(deadline_date);
CREATE INDEX IF NOT EXISTS idx_deadlines_org ON case_deadlines(org_id);

CREATE TRIGGER update_deadlines_updated_at
    BEFORE UPDATE ON case_deadlines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 5. MOTIONS & PLEADINGS
-- ============================================================

CREATE TABLE IF NOT EXISTS motions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    motion_type     TEXT    NOT NULL,
    -- demurrer, motion_to_compel, msj, msa, motion_in_limine,
    -- motion_to_strike, ex_parte, motion_for_sanctions,
    -- motion_for_protective_order, opposition, reply

    title           TEXT    NOT NULL,
    filing_party    TEXT,   -- plaintiff, defendant

    -- Document references
    document_id     UUID,   -- FK to uploaded_files or generated doc
    supporting_docs UUID[], -- array of document IDs

    -- Dates
    filed_date      DATE,
    hearing_date    DATE,
    hearing_time    TIME,
    department      TEXT,
    opposition_due  DATE,
    reply_due       DATE,

    -- Status
    status          TEXT    DEFAULT 'draft',
    -- draft -> filed -> opposition_received -> reply_filed -> heard -> decided
    ruling          TEXT,   -- granted, denied, granted_in_part, continued, off_calendar
    ruling_notes    TEXT,

    -- AI generation
    ai_generated    BOOLEAN DEFAULT false,
    ai_draft        TEXT,
    ai_analysis     TEXT,   -- strength assessment of motion or opposition

    -- Oversight agent flags
    oversight_flags JSONB   DEFAULT '[]',
    -- e.g. [{flag: "CCP 437c timing issue", severity: "high", recommendation: "..."}]

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_motions_case ON motions(case_id);
CREATE INDEX IF NOT EXISTS idx_motions_hearing ON motions(hearing_date);

CREATE TRIGGER update_motions_updated_at
    BEFORE UPDATE ON motions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 6. CONTRACT REVIEWS
-- ============================================================

CREATE TABLE IF NOT EXISTS contract_reviews (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        REFERENCES cases(id) ON DELETE SET NULL,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    contract_type   TEXT    NOT NULL,
    -- employment_agreement, nda, settlement_agreement, protective_order,
    -- retainer_agreement, vendor_contract, lease, partnership, other

    title           TEXT    NOT NULL,
    document_id     UUID,   -- FK to uploaded_files

    -- AI analysis
    ai_summary      TEXT,
    key_terms       JSONB   DEFAULT '[]',
    -- [{term, clause_number, favorable, risk_level, recommendation}]

    risk_flags      JSONB   DEFAULT '[]',
    -- [{flag, severity, clause, recommendation}]

    missing_clauses JSONB   DEFAULT '[]',
    -- [{clause, importance, recommended_language}]

    redline_suggestions JSONB DEFAULT '[]',
    -- [{original_text, suggested_text, reason}]

    overall_risk    TEXT,   -- low, medium, high, critical
    recommendation  TEXT,   -- approve, revise, reject, negotiate

    reviewed_by     UUID    REFERENCES auth.users(id) ON DELETE SET NULL,
    status          TEXT    DEFAULT 'pending', -- pending, reviewed, approved, rejected

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contracts_org ON contract_reviews(org_id);
CREATE INDEX IF NOT EXISTS idx_contracts_case ON contract_reviews(case_id);

CREATE TRIGGER update_contracts_updated_at
    BEFORE UPDATE ON contract_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 7. DEPOSITION PREP
-- ============================================================

CREATE TABLE IF NOT EXISTS deposition_preps (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    deponent_name       TEXT    NOT NULL,
    deponent_role       TEXT,   -- plaintiff, defendant, witness, expert, corporate_designee
    deposition_date     DATE,
    deposition_location TEXT,
    deposition_type     TEXT    DEFAULT 'oral', -- oral, written

    -- Prep materials
    outline             TEXT,
    key_documents       UUID[], -- uploaded_files IDs
    areas_of_inquiry    JSONB   DEFAULT '[]',
    -- [{area, objectives, key_questions, documents_to_use, pitfalls}]

    -- For defending depos
    prep_instructions   TEXT,   -- instructions for the deponent
    anticipated_questions JSONB DEFAULT '[]',
    objection_strategy  TEXT,

    -- Practice session
    practice_transcript TEXT,
    practice_score      NUMERIC(3,1),
    practice_feedback   TEXT,

    -- Post-depo
    transcript_doc_id   UUID,   -- uploaded depo transcript
    ai_summary          TEXT,
    key_admissions      JSONB   DEFAULT '[]',
    impeachment_material JSONB  DEFAULT '[]',

    status          TEXT    DEFAULT 'preparing', -- preparing, scheduled, completed, summarized

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_depo_case ON deposition_preps(case_id);

CREATE TRIGGER update_depo_updated_at
    BEFORE UPDATE ON deposition_preps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 8. VERDICT / SETTLEMENT LIBRARY
-- ============================================================

CREATE TABLE IF NOT EXISTS verdict_library (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID        REFERENCES organizations(id) ON DELETE SET NULL,

    -- Case identification
    case_name       TEXT    NOT NULL,
    case_number     TEXT,
    court           TEXT,   -- e.g. Los Angeles Superior Court
    county          TEXT,
    judge           TEXT,
    filing_date     DATE,
    resolution_date DATE,

    -- Case details
    case_type       TEXT,   -- FEHA, wrongful_termination, wage_hour, PI, etc.
    causes_of_action TEXT[],
    protected_class TEXT[],
    industry        TEXT,
    employer_size   TEXT,   -- small, medium, large, Fortune_500

    -- Outcome
    resolution_type TEXT    NOT NULL,
    -- jury_verdict, bench_verdict, settlement, dismissal, summary_judgment, arbitration_award
    verdict_amount  NUMERIC(14,2),
    economic_damages NUMERIC(14,2),
    non_economic_damages NUMERIC(14,2),
    punitive_damages NUMERIC(14,2),
    attorney_fees   NUMERIC(14,2),

    -- Key factors
    key_facts       TEXT,
    notable_rulings TEXT,
    plaintiff_counsel TEXT,
    defense_counsel TEXT,

    -- Source / provenance
    source_type     TEXT,   -- public_record, scraped, manual_entry, court_database
    source_url      TEXT,
    document_id     UUID,   -- uploaded document if available

    -- AI enrichment
    ai_summary      TEXT,
    comparable_factors JSONB DEFAULT '[]',
    -- [{factor, value, weight}] — for case valuation comparison

    verified        BOOLEAN DEFAULT false,

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verdict_type ON verdict_library(case_type);
CREATE INDEX IF NOT EXISTS idx_verdict_resolution ON verdict_library(resolution_type);
CREATE INDEX IF NOT EXISTS idx_verdict_amount ON verdict_library(verdict_amount);
CREATE INDEX IF NOT EXISTS idx_verdict_county ON verdict_library(county);

CREATE TRIGGER update_verdict_updated_at
    BEFORE UPDATE ON verdict_library
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- 9. CASE TIMELINE — Ordered chronological events
-- ============================================================

CREATE TABLE IF NOT EXISTS case_timeline (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID        NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id      UUID        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    event_date      DATE    NOT NULL,
    event_time      TIME,
    title           TEXT    NOT NULL,
    description     TEXT,
    event_type      TEXT,
    -- filing, discovery, hearing, deposition, mediation, trial, deadline, milestone
    auto_generated  BOOLEAN DEFAULT false,
    source_id       UUID,   -- ID from originating table (motion, discovery_set, etc.)
    source_table    TEXT,   -- which table the event originated from

    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_timeline_case ON case_timeline(case_id, event_date);


-- ============================================================
-- RLS POLICIES
-- ============================================================

ALTER TABLE client_intakes ENABLE ROW LEVEL SECURITY;
ALTER TABLE intake_causes_of_action ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE motions ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE deposition_preps ENABLE ROW LEVEL SECURITY;
ALTER TABLE verdict_library ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_timeline ENABLE ROW LEVEL SECURITY;

-- Org-scoped policies for all new tables
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY[
        'client_intakes', 'intake_causes_of_action', 'case_facts',
        'discovery_sets', 'case_deadlines', 'motions',
        'contract_reviews', 'deposition_preps', 'case_timeline'
    ]) LOOP
        EXECUTE format(
            'CREATE POLICY "Org members can view %1$s" ON %1$s FOR SELECT USING (org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()))',
            tbl
        );
        EXECUTE format(
            'CREATE POLICY "Org members can insert %1$s" ON %1$s FOR INSERT WITH CHECK (org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()))',
            tbl
        );
        EXECUTE format(
            'CREATE POLICY "Org members can update %1$s" ON %1$s FOR UPDATE USING (org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()))',
            tbl
        );
        EXECUTE format(
            'CREATE POLICY "Service role full access to %1$s" ON %1$s FOR ALL TO service_role USING (true) WITH CHECK (true)',
            tbl
        );
    END LOOP;
END
$$;

-- Verdict library: globally readable, org-scoped for writes
CREATE POLICY "Anyone can view verdict library"
    ON verdict_library FOR SELECT USING (true);
CREATE POLICY "Org members can insert verdicts"
    ON verdict_library FOR INSERT
    WITH CHECK (org_id IN (SELECT om.org_id FROM org_members om WHERE om.user_id = auth.uid()) OR org_id IS NULL);
CREATE POLICY "Service role full access to verdict_library"
    ON verdict_library FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Discovery items inherit from sets
CREATE POLICY "Org members can view discovery items"
    ON discovery_items FOR SELECT
    USING (set_id IN (SELECT ds.id FROM discovery_sets ds JOIN org_members om ON ds.org_id = om.org_id WHERE om.user_id = auth.uid()));
CREATE POLICY "Org members can insert discovery items"
    ON discovery_items FOR INSERT
    WITH CHECK (set_id IN (SELECT ds.id FROM discovery_sets ds JOIN org_members om ON ds.org_id = om.org_id WHERE om.user_id = auth.uid()));
CREATE POLICY "Service role full access to discovery_items"
    ON discovery_items FOR ALL TO service_role USING (true) WITH CHECK (true);
