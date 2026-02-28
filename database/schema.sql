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
