# ⚡ CaseCommand — AI Litigation Practice Server

An agentic litigation operating system: an AI paralegal that **works your
cases around the clock** — triaging deadlines, drafting complete work
product, and staging everything in an attorney review queue — plus an
interactive CaseCommander agent that can actually *do* things, not just chat.

## How the autonomy works

```
                    ┌────────────────────────────────────────────┐
                    │       AUTONOMOUS PARALEGAL WORKER          │
  every hour ──────▶│  1. deterministic deadline sweep (no AI)   │
                    │  2. agentic cycle: triage, task, DRAFT     │
                    │  3. daily digest                           │
                    └───────────────┬────────────────────────────┘
                                    │ everything lands in the DB
                                    ▼
   ┌─────────────┐        ┌──────────────────┐       ┌──────────────────────┐
   │  Agent tools │───────▶│  ATTORNEY REVIEW │──────▶│ attorney approves &  │
   │  (13 tools,  │        │  QUEUE (/admin)  │       │ personally sends /   │
   │ audit-logged)│        │ approve / reject │       │ files (human act)    │
   └─────────────┘        └──────────────────┘       └──────────────────────┘
```

**The critical design decision:** the agents have *no tools that can reach
outside the practice*. No email, no filing, no service. They prepare; the
attorney reviews, approves, and sends. This is not a limitation — it is the
architecture California professional responsibility requires:

- **RPC 5.3 / ABA Formal Op. 512** — AI is supervised like a nonlawyer
  assistant; the audit log is your supervision record.
- **Proposed CA RPC 1.1 amendment (2026)** — independent attorney
  verification of every AI output used in a representation.
- **Noland v. Land of the Free (Cal. Ct. App. 2025)** — $10K sanctions for
  unverified AI citations. Every AI draft containing citations here
  auto-generates a mandatory "verify citations" task.
- **RPC 1.2(a)** — settlement decisions belong to the client; the agent
  analyzes and recommends only.

## What the agents can do

| Capability | How |
|---|---|
| **Autonomous cycles** | Background worker runs hourly: sweeps deadlines → tasks, drafts due documents, writes daily digest |
| **Agentic chat** | Tell CaseCommander "we got discovery responses from Smith Trucking today, served by mail" → it computes the 45-day motion deadline, calendars it, creates tasks, and starts the M&C letter |
| **CA deadline engine** | `rules.py` computes CCP/CRC deadlines from trigger events: court-day math, holiday rolls, §1013/§1010.6 service extensions, trial-anchored chains (MSJ, expert exchange, discovery cutoffs, §998) |
| **Drafting on demand** | `/api/agent/draft` or the dashboard: M&C letters, motions, separate statements, complaints, demand letters, cross outlines |
| **Review queue** | `/admin` dashboard: read full drafts, approve/reject with notes, one-click task completion |
| **Supervision trail** | Every agent action audit-logged; every cycle recorded with token usage |

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env       # add your ANTHROPIC_API_KEY
python server.py
```

- **http://localhost:3000** — case UI
- **http://localhost:3000/admin** — paralegal dashboard & review queue
- **http://localhost:3000/docs** — full API docs (Swagger)

The paralegal worker starts automatically (hourly by default). Trigger a
cycle immediately with the dashboard button or `POST /api/agent/cycle`.
Even with no API key, the deterministic deadline sweep still runs — nothing
falls through the cracks.

## Deploy to Render

1. Push to GitHub → Render **New → Web Service** → auto-detects `render.yaml`
   (includes a persistent disk so the database survives deploys)
2. Set environment variables:
   - `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com/settings/keys)
   - `AUTH_TOKEN` — **required in practice** (client data!):
     `python -c "import secrets; print(secrets.token_urlsafe(32))"`

## Models & cost controls

| Setting | Default | Why |
|---|---|---|
| `CLAUDE_MODEL` | `claude-opus-4-8` | Anthropic's recommended agentic model — chat + drafting quality |
| `WORKER_MODEL` | `claude-sonnet-5` | Near-Opus agentic quality at the high-volume price tier for hourly cycles |
| `PARALEGAL_INTERVAL` | `3600` | Cycle frequency in seconds (0 disables) |
| `CYCLE_MAX_ITERATIONS` | `12` | Hard cap on tool-use rounds per cycle — bounds API spend |

Prompt caching is enabled on the system prompt (`cache_control: ephemeral`),
cutting repeat-context input cost by up to ~90% across agent iterations.
Note: new-generation models (Opus 4.7+, Sonnet 5) no longer accept
`temperature` — the client handles this automatically.

## API

```
# Agentic
POST   /api/chat                     CaseCommander (multi-turn, uses tools)
POST   /api/agent/cycle              Run a paralegal cycle now
POST   /api/agent/draft              Draft a document into the review queue
GET    /api/agent/runs               Cycle history (with token usage)

# Review queue (the human-in-the-loop gate)
GET    /api/review/queue             Pending docs + urgent tasks + deadlines
GET    /api/documents[/{id}]         List / read drafts
POST   /api/documents/{id}/review    {action: approve|reject, note}

# Practice data
GET/POST /api/cases, PUT/DELETE /api/cases/{id}
GET/POST /api/tasks, PATCH /api/tasks/{id}
GET/POST /api/deadlines
POST   /api/deadlines/compute        CA deadline math from a trigger event
GET    /api/audit                    Supervision audit trail
GET    /api/health                   Status incl. worker state (public)
POST   /api/ai, GET /api/digest      Legacy endpoints for the bundled UI
```

## Files

```
server.py          FastAPI app: routes, auth, rate limiting, middleware
agent.py           Agentic loop + system prompts (incl. ethics constraints)
tools.py           13 agent tools — all DB-only, all audit-logged
worker.py          Autonomous paralegal scheduler
rules.py           California deadline rules engine (CCP/CRC/Gov C)
claude_client.py   Anthropic API client: pooling, retries, caching, tool use
database.py        SQLite: cases, documents, tasks, deadlines, audit, runs
static/admin.html  Attorney dashboard / review queue
tests/             126 tests
```

## Testing

```bash
python -m pytest tests/ -v      # 126 tests, no API key needed (AI mocked)
```

## Ethics & supervision model (read this)

This system is built for **autonomous preparation with supervised output**:

1. **The agent works continuously without being asked** — but its universe
   ends at the database. It cannot communicate with courts, opposing
   counsel, or clients.
2. **You review everything before it leaves** — the `/admin` queue is the
   single choke point. Approving marks work product ready; *sending remains
   a human act you perform yourself.*
3. **Citations are never trusted** — any draft containing legal citations
   generates a mandatory verification task before you approve.
4. **Everything is logged** — the audit trail documents your supervision
   for RPC 5.3 compliance.
5. **Deadline math is a drafting aid** — every computed date carries a
   verification flag; check local rules and standing orders.

## Roadmap (next integrations)

- **Citations API grounding** — attach case documents to drafting calls so
  every factual assertion carries a pinpoint citation to the record
  (Anthropic Citations API; eliminates source hallucination)
- **Document ingestion** — upload discovery responses/medical records for
  grounded analysis (today you paste text via chat)
- **Email/calendar via MCP** — *read* incoming mail to auto-detect trigger
  events; outbound remains behind the approval gate
- **Batch API overnight review** — 50% cost reduction for bulk document
  review runs
- **Claude for Legal plugins** — Anthropic's litigation practice plugins
  and legal MCP connectors (Westlaw, Everlaw, Trellis) as they fit
