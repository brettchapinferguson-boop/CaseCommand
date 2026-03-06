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
