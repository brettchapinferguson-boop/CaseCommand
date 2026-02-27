# CaseCommand v2.0 — Agentic AI Litigation Operating System

## Quick Start Deployment

### Step 1: Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Go to **SQL Editor** and paste the contents of `sql/001_schema.sql`
3. Click **Run** to create all tables, indexes, and policies
4. Go to **Settings > API** and copy:
   - Project URL → `SUPABASE_URL`
   - `anon` public key → `SUPABASE_KEY`  
   - `service_role` key → `SUPABASE_SERVICE_KEY`

### Step 2: Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) > **New > Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml`
5. Add environment variables:
   - `ANTHROPIC_API_KEY` — your Anthropic API key
   - `SUPABASE_URL` — from Step 1
   - `SUPABASE_KEY` — from Step 1
   - `SUPABASE_SERVICE_KEY` — from Step 1
6. Deploy!

### Step 3: Use It

- Open your Render URL in a browser
- Upload a PDF → Choose "Create New Case" → Click "Process with AI"
- Open CaseCommander chat and tell it what to do

## Local Development

```bash
cd backend
cp .env.example .env
# Fill in your keys in .env

pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Frontend is served at `http://localhost:8000`

## Project Structure

```
casecommand-v2/
├── backend/
│   ├── server.py              # FastAPI main server (all endpoints)
│   ├── config.py              # Environment/settings
│   ├── database.py            # Supabase client wrapper
│   ├── document_pipeline.py   # Upload → Extract → Analyze → Create Case
│   ├── agent.py               # Agentic chat with 11 tools + function calling
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html             # Complete React dashboard (single file)
├── sql/
│   └── 001_schema.sql         # Supabase database schema
├── Dockerfile
├── render.yaml
└── README.md
```

## What's Working (Phase 1)

- ✅ Document upload with PDF text extraction
- ✅ AI-powered document classification and analysis
- ✅ New case creation from uploaded documents
- ✅ Add documents to existing cases
- ✅ Case dashboard with facts, timeline, documents, and analysis
- ✅ Agentic chatbot with 11 tools (function calling)
- ✅ Chat can create cases, generate documents, propose calendar/email actions
- ✅ Human-in-the-loop approval queue for external actions
- ✅ Persistent conversation history
- ✅ Action audit log

## Coming Next

- **Phase 2** (Weeks 3-4): Real-time UI updates via WebSocket
- **Phase 3** (Weeks 5-7): Google Calendar, Gmail, Clio integrations via n8n
- **Phase 4** (Week 8): WhatsApp access via Twilio
- **Phase 5** (Weeks 9-10): Memory, learning, self-improvement system
- **Phase 6** (Weeks 11-12): Security hardening, multi-user, SaaS readiness
