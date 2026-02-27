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

## Run Locally (Alternative)

```bash
# 1. Install dependencies
pip install fastapi uvicorn httpx

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
casecommand-prod/
├── server.py          # FastAPI server (all routes + AI calls)
├── static/
│   └── index.html     # Bundled React frontend (343KB)
├── .env.example       # Template config
├── .env               # Your config (create this)
├── requirements.txt   # Python dependencies
├── start.sh           # One-command launcher
└── README.md          # This file
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

## Troubleshooting

**"No API key" on startup?**
→ Edit `.env` and add your `ANTHROPIC_API_KEY`

**Port 3000 in use?**
→ `python -m uvicorn server:app --port 8000`

**Want to access from phone/other device?**
→ Already listening on `0.0.0.0` — use your computer's IP: `http://192.168.x.x:3000`
