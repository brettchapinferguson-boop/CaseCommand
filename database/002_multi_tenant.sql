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
