# ⚡ CaseCommand — Production Server

AI-powered litigation operating system. One server, everything works.

## Deploy to Render (Recommended)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just click **Create Web Service**
5. In the Render dashboard → **Environment** → Add:
   - `ANTHROPIC_API_KEY` = your key from [console.anthropic.com](https://console.anthropic.com/settings/keys)
6. Render deploys. You get a URL like `https://casecommand.onrender.com`

That's it. Open the URL on any device — phone, laptop, tablet.

## Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env → paste your Anthropic API key
# Get one at: https://console.anthropic.com/settings/keys

# 3. Run
python server.py
```

Open **http://localhost:3000** — that's it.

No browser API keys. No CORS issues. No configuration screens.
Your API key lives in `.env` on the server and never touches the browser.

## Run with Docker

```bash
docker build -t casecommand .
docker run -p 3000:3000 --env-file .env casecommand
```

## What You Get

| Feature | How |
|---------|-----|
| **Dashboard** | All cases, deadlines, portfolio valuation at a glance |
| **Case View** | Full case detail with timeline, modules, activity |
| **⚡ CaseCommander** | Multi-turn AI chat with full case context (click the ⚡ button) |
| **🔍 DisputeFlow** | Paste discovery responses → AI deficiency analysis |
| **✉️ M&C Letters** | Click Generate M&C → complete meet & confer letter |
| **⚖️ Motion Cascade** | Separate statement + motion + declaration + order |
| **⚖️ Cross Outlines** | 25+ question examination outlines with source citations |
| **🤝 Settlement** | Data-driven valuation with comparable verdict analysis |
| **📄 Complaints** | Draft complete California complaints with all COAs |

## Files

```
casecommand/
├── server.py              # FastAPI server (all routes + AI calls)
├── index.html             # Bundled React frontend
├── .env.example           # Template config
├── .env                   # Your config (create from .env.example)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container deployment
├── render.yaml            # Render.com deployment config
├── start.sh               # One-command launcher
├── tests/                 # Test suite
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_cases.py
│   ├── test_chat.py
│   ├── test_deadlines.py
│   ├── test_sessions.py
│   └── test_rate_limit.py
└── .github/workflows/
    └── ci.yml             # GitHub Actions CI
```

## API Endpoints

```
GET  /              → Serves the UI
GET  /api/health    → Server status
GET  /api/cases     → All cases
GET  /api/cases/:id → Single case
POST /api/chat      → CaseCommander conversation
POST /api/ai        → Generic AI call (any module)
GET  /api/deadlines → All upcoming deadlines
GET  /api/digest    → AI-generated daily digest
GET  /docs          → Swagger API documentation
```

## Configuration

All configuration is via environment variables. See `.env.example` for the full list.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-5-20250514` | Claude model to use |
| `PORT` | No | `3000` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated) |
| `SESSION_TTL_SECONDS` | No | `3600` | Session expiry time |
| `MAX_SESSIONS` | No | `1000` | Max concurrent sessions |
| `RATE_LIMIT_REQUESTS` | No | `30` | Max AI requests per window |
| `RATE_LIMIT_WINDOW` | No | `60` | Rate limit window (seconds) |

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Production Features

- **Structured logging** with configurable log level
- **Security headers** (X-Content-Type-Options, X-Frame-Options, etc.)
- **CORS** with configurable allowed origins
- **Rate limiting** on AI endpoints (per-IP)
- **Input validation** with size limits on all user inputs
- **Session management** with TTL-based cleanup and capacity limits
- **Request tracking** via X-Request-ID header
- **Graceful shutdown** with background task cleanup

## Troubleshooting

**"No API key" on startup?**
→ Edit `.env` and add your `ANTHROPIC_API_KEY`

**Port 3000 in use?**
→ `PORT=8000 python server.py`

**Want to access from phone/other device?**
→ Already listening on `0.0.0.0` — use your computer's IP: `http://192.168.x.x:3000`
