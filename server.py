"""
CaseCommand Production Server
==============================
One server. Everything works. No browser API keys.

Setup:
  1. cp .env.example .env
  2. Add your ANTHROPIC_API_KEY to .env
  3. pip install fastapi uvicorn httpx
  4. python server.py

Then open http://localhost:3000
"""

import os, json, uuid, httpx, asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Load .env ──────────────────────────────────────
def load_env():
    for p in [Path(__file__).parent / ".env", Path.home() / ".env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            return
load_env()

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250514")

# ── FastAPI ────────────────────────────────────────
app = FastAPI(title="CaseCommand", version="2.0")

# ── Sessions (in-memory; production: Redis/Supabase) ──
sessions: Dict[str, Dict] = {}
def get_session(sid: str) -> Dict:
    if sid not in sessions:
        sessions[sid] = {"id": sid, "history": [], "created": datetime.now().isoformat()}
    return sessions[sid]

# ── Request Models ──
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    current_case_id: Optional[str] = None

class AIRequest(BaseModel):
    system: str
    message: str
    max_tokens: int = 4096
    temperature: float = 0.3

# ── Demo Cases ──
PHASES = ["Pre-Suit","Filing","Pleadings","Discovery","Depositions","Experts","Motions","Pre-Trial","Trial"]
CASES = [
    {"id":"c1","name":"Rodriguez v. Smith Trucking","number":"24STCV12345","type":"Personal Injury",
     "client":"Maria Rodriguez","opposing":"Smith Trucking, Inc.","phase":3,"specials":88000,
     "valuation":{"lo":150,"mid":275,"hi":450},
     "deadline":{"date":"Mar 11","text":"45-Day Discovery Motion","urgent":True},
     "modules":{
         "pleadings":{"status":"complete","label":"5 COAs filed","detail":"Negligence, MV Neg, Respondeat Superior, Neg Entrustment, Neg Per Se"},
         "discovery":{"status":"active","label":"5 deficient responses","detail":"M&C letter drafted"},
         "trial":{"status":"building","label":"Cross: J. Smith (25 Qs)","detail":"6 chapters, 15 source-linked"},
         "settlement":{"status":"monitoring","label":"Post-discovery trigger","detail":"Reassess after discovery"},
     }},
    {"id":"c2","name":"Chen v. Pacific Properties","number":"25STCV02890","type":"Premises Liability",
     "client":"David Chen","opposing":"Pacific Properties LLC","phase":2,"specials":34500,
     "valuation":{"lo":55,"mid":95,"hi":165},
     "deadline":{"date":"Mar 28","text":"Defendant Response Due","urgent":False},
     "modules":{
         "pleadings":{"status":"complete","label":"3 COAs filed","detail":"Premises Liability, Negligence, Breach"},
         "discovery":{"status":"pending","label":"After answer","detail":"Prepare once defendant answers"},
         "settlement":{"status":"active","label":"Demand sent: $85K","detail":"Response due Mar 15"},
     }},
    {"id":"c3","name":"Williams v. TechStart","number":None,"type":"Employment — FEHA",
     "client":"Angela Williams","opposing":"TechStart Inc.","phase":1,"specials":128000,
     "valuation":{"lo":200,"mid":425,"hi":750},
     "deadline":{"date":"Mar 1","text":"Complete Intake & File","urgent":True},
     "modules":{
         "pleadings":{"status":"active","label":"Analyzing 5 COAs","detail":"WT, Discrim, Harassment, Retaliation, Breach"},
         "settlement":{"status":"assessing","label":"High-value FEHA","detail":"Recommend filing first for leverage"},
     }},
]

def get_case(cid: str): return next((c for c in CASES if c["id"] == cid), None)

# ── CaseCommander System Prompt ──
def build_prompt(case: Optional[Dict] = None) -> str:
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    p = f"""You are CaseCommander, the AI litigation intelligence system for LawClaw.

You serve Brett Ferguson (California attorney, SBN 281519, Law Office of Brett Ferguson, Long Beach).

You are NOT a chatbot. You are co-counsel — an intelligent agent that knows every case, deadline, and strategic consideration.

CORE PRINCIPLES:
1. PROACTIVE: Alert on deadlines, flag opportunities, recommend actions.
2. SPECIFIC: Reference specific case data, dates, numbers. Never generic.
3. SOURCE-GROUNDED: Every assertion traces to a document or database.
4. STRATEGIC: Connect actions to litigation strategy and case outcomes.
5. COMPLIANT: California law, RPC, best practices always.
6. EFFICIENT: Draft the document, don't describe it.

NEVER: fabricate citations, contact represented parties (RPC 4.2), make settlement decisions for client (RPC 1.2(a)).

DATE: {now}

═══ ACTIVE CASES ═══
"""
    for c in CASES:
        phase = PHASES[c["phase"]] if c["phase"] < len(PHASES) else "?"
        urg = f" ⚠️ URGENT: {c['deadline']['text']} ({c['deadline']['date']})" if c.get("deadline",{}).get("urgent") else ""
        p += f"• {c['name']} | {c['type']} | {phase} | ${c['specials']:,} specials | ${c['valuation']['mid']}K mid{urg}\n"

    if case:
        phase = PHASES[case["phase"]] if case["phase"] < len(PHASES) else "?"
        p += f"""
═══ FOCUSED: {case['name']} ═══
Number: {case.get('number') or 'Pre-filing'}
Type: {case['type']}
Client: {case['client']}
Opposing: {case['opposing']}
Phase: {phase}
Specials: ${case['specials']:,}
Valuation: ${case['valuation']['lo']}K / ${case['valuation']['mid']}K / ${case['valuation']['hi']}K
"""
        if case.get("modules"):
            p += "\nMODULES:\n"
            for k, m in case["modules"].items():
                p += f"  [{m['status'].upper()}] {k}: {m['label']} — {m['detail']}\n"

    p += """
═══ LEGAL KNOWLEDGE ═══
CCP §2030.210-250 (interrogatories), CCP §2031.210-240 (RFP), CCP §2016.040 (M&C),
CCP §§2030.300(c)/2031.310(c) (45-day JURISDICTIONAL deadline), CRC 3.1345 (separate statement),
Korea Data Systems (boilerplate=sanctionable), Deyo v. Kilbourne ("continuing"=non-compliant),
Hernandez v. Superior Court (privilege log), CCP §998 (cost-shifting), RPC 4.2, 1.1, 1.3, 3.3.

═══ VERDICT DATA ═══
PI Trucking (LA): $325K-$2.1M. Median multiplier: 6.2x. Mediation: $325K-$475K.
FEHA (LA): $185K-$3.2M. Discrimination >> harassment. Punitive common.
Judge Buckley: 61% plaintiff, $1.1M avg, strict M&C.
Judge Scheper: 52% plaintiff, $420K avg, pushes settlement.

STYLE: Lead with most important info. Be direct. Specific numbers/dates/cases. End with next steps. If asked to draft, DRAFT IT."""
    return p


# ── Claude API (server-side) ──
async def call_claude(system: str, messages: List[Dict], max_tokens: int = 4096, temperature: float = 0.3) -> Dict:
    if not API_KEY:
        return {"success": False, "text": "", "error": "No API key. Add ANTHROPIC_API_KEY to .env"}

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages[-20:],
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
                return {"success": True, "text": text, "usage": data.get("usage", {})}
            if resp.status_code in (429, 529):
                await asyncio.sleep((2 ** attempt) * 2)
                continue
            return {"success": False, "text": "", "error": f"Anthropic API {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "text": "", "error": str(e)}

    return {"success": False, "text": "", "error": "Max retries exceeded"}


# ══════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the CaseCommand UI."""
    for path in [
        Path(__file__).parent / "static" / "index.html",
        Path(__file__).parent / "index.html",
        Path(__file__).parent / "casecommand-ui.html",
    ]:
        if path.exists():
            return HTMLResponse(content=path.read_text())
    return HTMLResponse("<h1>CaseCommand server running. Place index.html in static/</h1>")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(API_KEY),
        "model": MODEL,
        "cases": len(CASES),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/cases")
async def list_cases():
    return {"cases": CASES}


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    c = get_case(case_id)
    if not c: raise HTTPException(404, "Case not found")
    return c


@app.post("/api/chat")
async def commander_chat(req: ChatRequest):
    """CaseCommander multi-turn chat with session tracking."""
    sid = req.session_id or str(uuid.uuid4())
    session = get_session(sid)

    case = get_case(req.current_case_id) if req.current_case_id else None
    system = build_prompt(case)

    session["history"].append({"role": "user", "content": req.message})

    result = await call_claude(system, session["history"])

    if result["success"]:
        session["history"].append({"role": "assistant", "content": result["text"]})
        return {"response": result["text"], "session_id": sid, "usage": result.get("usage")}
    else:
        return {"response": f"Error: {result['error']}", "session_id": sid}


@app.post("/api/ai")
async def generic_ai(req: AIRequest):
    """Generic AI endpoint — any module sends system + message, gets response."""
    result = await call_claude(
        req.system,
        [{"role": "user", "content": req.message}],
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    if result["success"]:
        return {"success": True, "text": result["text"], "usage": result.get("usage")}
    raise HTTPException(500, result["error"])


@app.get("/api/deadlines")
async def deadlines():
    dl = [{"case": c["name"], "case_id": c["id"], **c["deadline"]} for c in CASES if c.get("deadline")]
    dl.sort(key=lambda d: (not d.get("urgent"), d.get("date","")))
    return {"deadlines": dl}


@app.get("/api/digest")
async def daily_digest():
    result = await call_claude(
        build_prompt(),
        [{"role": "user", "content": "Generate a concise daily digest: all case statuses, urgent deadlines, pending actions, and recommendations."}],
        max_tokens=2000,
    )
    if result["success"]:
        return {"digest": result["text"], "generated_at": datetime.now().isoformat()}
    raise HTTPException(500, result.get("error"))


# ══════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    k = "✅ API key loaded" if API_KEY else "❌ No API key — add to .env"
    port = os.environ.get("PORT", "3000")
    print(f"""
╔═══════════════════════════════════════════╗
║  ⚡ CaseCommand Server v2.0               ║
║                                           ║
║  {k:<40s}║
║  Model: {MODEL:<32s}║
║                                           ║
║  → http://localhost:{port:<21s}║
╚═══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=os.environ.get("RENDER") is None)
