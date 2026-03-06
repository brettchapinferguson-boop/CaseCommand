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
