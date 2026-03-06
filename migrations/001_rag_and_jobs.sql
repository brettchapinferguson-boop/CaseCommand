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
