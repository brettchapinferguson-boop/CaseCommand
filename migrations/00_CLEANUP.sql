-- Run this FIRST if DEPLOY_FULL.sql fails with "policy already exists"
-- This drops all RLS policies so they can be cleanly re-created.
-- Safe to run multiple times.

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT policyname, tablename, schemaname
        FROM pg_policies
        WHERE schemaname IN ('public', 'storage')
    ) LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', r.policyname, r.schemaname, r.tablename);
        RAISE NOTICE 'Dropped policy % on %.%', r.policyname, r.schemaname, r.tablename;
    END LOOP;
END
$$;
