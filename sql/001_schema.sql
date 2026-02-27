-- ============================================================
-- CaseCommand v2.0 - Supabase Database Schema
-- Run this in Supabase SQL Editor
-- ============================================================

-- Enable pgvector for embeddings
create extension if not exists vector;

-- ============================================================
-- CASES - Master case records
-- ============================================================
create table public.cases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  name text not null,                    -- e.g., "Ruiz v. Zeller"
  case_number text,                      -- court case number
  case_type text,                        -- employment, personal_injury, civil_rights, etc.
  status text default 'active' check (status in ('active', 'discovery', 'trial_prep', 'trial', 'settled', 'closed', 'archived')),
  court text,                            -- e.g., "Los Angeles Superior Court"
  judge text,
  department text,
  
  -- Parties (JSONB for flexibility)
  plaintiff jsonb default '[]'::jsonb,   -- [{name, role, attorney, contact}]
  defendant jsonb default '[]'::jsonb,
  other_parties jsonb default '[]'::jsonb,
  
  -- AI-generated analysis
  summary text,                          -- AI case summary
  key_issues jsonb default '[]'::jsonb,  -- ["wrongful termination", "retaliation"]
  causes_of_action jsonb default '[]'::jsonb, -- [{name, statute, elements, strength}]
  strengths jsonb default '[]'::jsonb,
  weaknesses jsonb default '[]'::jsonb,
  
  -- Metadata
  filing_date date,
  trial_date date,
  next_deadline date,
  next_deadline_description text,
  
  -- Clio integration
  clio_matter_id text,
  
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- DOCUMENTS - All uploaded files linked to cases
-- ============================================================
create table public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  
  -- File info
  filename text not null,
  file_path text not null,               -- Supabase Storage path
  file_size bigint,
  file_type text,                        -- pdf, docx, txt, image
  mime_type text,
  
  -- Classification
  doc_type text,                         -- complaint, answer, motion, deposition, exhibit, brief, correspondence, discovery, declaration, other
  doc_subtype text,                      -- e.g., "trial_brief", "msj", "interrogatories"
  
  -- Extracted content
  extracted_text text,                   -- Full text from PDF
  page_count integer,
  
  -- AI analysis
  summary text,
  key_facts jsonb default '[]'::jsonb,
  parties_mentioned jsonb default '[]'::jsonb,
  dates_mentioned jsonb default '[]'::jsonb,
  legal_issues jsonb default '[]'::jsonb,
  
  -- Processing status
  processing_status text default 'pending' check (processing_status in ('pending', 'processing', 'completed', 'failed')),
  processing_error text,
  
  -- Vector embedding for RAG
  embedding vector(1536),
  
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- CASE_FACTS - Extracted facts from documents
-- ============================================================
create table public.case_facts (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  
  fact_text text not null,
  fact_type text,                        -- admission, testimony, evidence, allegation, undisputed
  category text,                         -- liability, damages, credibility, timeline, procedural
  source_page integer,
  source_quote text,                     -- exact quote from document
  
  -- For cross-referencing
  related_party text,
  related_date date,
  
  -- Confidence and verification
  confidence float default 0.8,
  verified_by_attorney boolean default false,
  attorney_notes text,
  
  -- Vector embedding
  embedding vector(1536),
  
  created_at timestamptz default now()
);

-- ============================================================
-- TIMELINE_EVENTS - Chronological case events
-- ============================================================
create table public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
  
  event_date date not null,
  event_time time,
  title text not null,
  description text,
  event_type text,                       -- filing, hearing, deposition, deadline, discovery, settlement, incident, other
  
  -- Deadline tracking
  is_deadline boolean default false,
  deadline_status text check (deadline_status in ('upcoming', 'completed', 'overdue', 'waived')),
  
  -- Calendar sync
  google_calendar_event_id text,
  clio_task_id text,
  
  created_at timestamptz default now()
);

-- ============================================================
-- CONVERSATIONS - Chat history with AI
-- ============================================================
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete set null,
  user_id uuid references auth.users(id) on delete cascade,
  session_id text not null,              -- groups messages in a session
  
  role text not null check (role in ('user', 'assistant', 'system', 'tool')),
  content text not null,
  
  -- Function calling
  tool_calls jsonb,                      -- [{name, arguments, result}]
  tool_name text,                        -- if role='tool', which tool responded
  
  -- Metadata
  model text,                            -- claude-sonnet-4-5, claude-opus-4-6
  tokens_used integer,
  
  created_at timestamptz default now()
);

-- ============================================================
-- ACTION_LOG - Audit trail for all agent actions
-- ============================================================
create table public.action_log (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references public.cases(id) on delete set null,
  user_id uuid references auth.users(id) on delete cascade,
  
  action_type text not null,             -- email_sent, calendar_created, document_generated, case_created, clio_synced
  action_description text,
  
  -- The proposed action details
  action_payload jsonb,                  -- full details of what was proposed
  
  -- Approval workflow
  status text default 'pending' check (status in ('pending', 'approved', 'rejected', 'executed', 'failed')),
  approved_by uuid references auth.users(id),
  approved_at timestamptz,
  rejection_reason text,
  
  -- Execution result
  execution_result jsonb,
  error_message text,
  
  created_at timestamptz default now()
);

-- ============================================================
-- MEMORY_STORE - Persistent memory for self-improvement
-- ============================================================
create table public.memory_store (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  
  memory_type text not null,             -- preference, correction, pattern, style, case_insight
  memory_key text not null,              -- what this memory is about
  memory_value text not null,            -- the actual memory content
  
  -- Context
  case_id uuid references public.cases(id) on delete set null,
  case_type text,                        -- so patterns can be case-type specific
  
  -- For RAG retrieval
  embedding vector(1536),
  
  -- Usage tracking
  times_used integer default 0,
  last_used_at timestamptz,
  relevance_score float default 1.0,
  
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- PROMPT_TEMPLATES - Versioned, self-improving prompts
-- ============================================================
create table public.prompt_templates (
  id uuid primary key default gen_random_uuid(),
  name text not null,                    -- e.g., "cross_exam_generator", "case_summary"
  version integer default 1,
  template text not null,
  
  -- Performance tracking
  times_used integer default 0,
  thumbs_up integer default 0,
  thumbs_down integer default 0,
  edit_rate float default 0.0,           -- % of outputs that were edited
  performance_score float default 0.5,
  
  is_active boolean default true,
  
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  
  unique(name, version)
);

-- ============================================================
-- INDEXES
-- ============================================================
create index idx_cases_user on public.cases(user_id);
create index idx_cases_status on public.cases(status);
create index idx_documents_case on public.documents(case_id);
create index idx_documents_status on public.documents(processing_status);
create index idx_case_facts_case on public.case_facts(case_id);
create index idx_timeline_case_date on public.timeline_events(case_id, event_date);
create index idx_conversations_session on public.conversations(session_id);
create index idx_conversations_case on public.conversations(case_id);
create index idx_action_log_case on public.action_log(case_id);
create index idx_action_log_status on public.action_log(status);
create index idx_memory_user_type on public.memory_store(user_id, memory_type);

-- Vector similarity indexes
create index idx_documents_embedding on public.documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_case_facts_embedding on public.case_facts using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_memory_embedding on public.memory_store using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table public.cases enable row level security;
alter table public.documents enable row level security;
alter table public.case_facts enable row level security;
alter table public.timeline_events enable row level security;
alter table public.conversations enable row level security;
alter table public.action_log enable row level security;
alter table public.memory_store enable row level security;
alter table public.prompt_templates enable row level security;

-- Users can only see their own data
create policy "Users see own cases" on public.cases for all using (auth.uid() = user_id);
create policy "Users see own documents" on public.documents for all using (auth.uid() = user_id);
create policy "Users see own facts" on public.case_facts for all using (case_id in (select id from public.cases where user_id = auth.uid()));
create policy "Users see own timeline" on public.timeline_events for all using (case_id in (select id from public.cases where user_id = auth.uid()));
create policy "Users see own conversations" on public.conversations for all using (auth.uid() = user_id);
create policy "Users see own actions" on public.action_log for all using (auth.uid() = user_id);
create policy "Users see own memory" on public.memory_store for all using (auth.uid() = user_id);
create policy "All users see active prompts" on public.prompt_templates for select using (is_active = true);

-- ============================================================
-- AUTO-UPDATE TIMESTAMPS
-- ============================================================
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger cases_updated_at before update on public.cases for each row execute function update_updated_at();
create trigger documents_updated_at before update on public.documents for each row execute function update_updated_at();
create trigger memory_updated_at before update on public.memory_store for each row execute function update_updated_at();
create trigger prompts_updated_at before update on public.prompt_templates for each row execute function update_updated_at();

-- ============================================================
-- STORAGE BUCKET for documents
-- ============================================================
insert into storage.buckets (id, name, public) values ('case-documents', 'case-documents', false);

create policy "Users upload own docs" on storage.objects for insert
  with check (bucket_id = 'case-documents' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "Users read own docs" on storage.objects for select
  using (bucket_id = 'case-documents' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "Users delete own docs" on storage.objects for delete
  using (bucket_id = 'case-documents' and auth.uid()::text = (storage.foldername(name))[1]);
