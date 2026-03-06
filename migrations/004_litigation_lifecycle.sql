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
