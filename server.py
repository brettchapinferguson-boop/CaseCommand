"""
CaseCommand Production Server
==============================
One server. Everything works. No browser API keys.

Setup:
  1. cp .env.example .env
  2. Add your ANTHROPIC_API_KEY to .env
  3. pip install -r requirements.txt
  4. python server.py

Then open http://localhost:3000
"""

import os
import json
import uuid
import time
import logging
import asyncio
import httpx

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ── Logging ───────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("casecommand")


# ── Load .env ─────────────────────────────────────
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
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# ── Session config ────────────────────────────────
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "3600"))
SESSION_CLEANUP_INTERVAL = int(os.environ.get("SESSION_CLEANUP_INTERVAL", "300"))
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "1000"))

# ── Rate limiting config ──────────────────────────
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

# ── Input limits ──────────────────────────────────
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "50000"))
MAX_SYSTEM_PROMPT_LENGTH = int(os.environ.get("MAX_SYSTEM_PROMPT_LENGTH", "100000"))


# ── Sessions (in-memory with TTL cleanup) ─────────
sessions: Dict[str, Dict] = {}
rate_limits: Dict[str, List[float]] = {}


def get_session(sid: str) -> Dict:
    if sid not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            _evict_oldest_session()
        sessions[sid] = {
            "id": sid,
            "history": [],
            "created": datetime.now().isoformat(),
            "last_accessed": time.time(),
        }
    else:
        sessions[sid]["last_accessed"] = time.time()
    return sessions[sid]


def _evict_oldest_session():
    """Evict the least recently used session when at capacity."""
    if not sessions:
        return
    oldest_sid = min(sessions, key=lambda s: sessions[s].get("last_accessed", 0))
    del sessions[oldest_sid]
    logger.info("Evicted oldest session %s (at capacity %d)", oldest_sid, MAX_SESSIONS)


async def _cleanup_expired_sessions():
    """Background task to remove expired sessions."""
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        now = time.time()
        expired = [
            sid
            for sid, s in sessions.items()
            if now - s.get("last_accessed", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions, %d remaining", len(expired), len(sessions))


# ── Rate Limiting ─────────────────────────────────
def _check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    if client_ip not in rate_limits:
        rate_limits[client_ip] = []

    # Remove timestamps outside the window
    rate_limits[client_ip] = [
        t for t in rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(rate_limits[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False

    rate_limits[client_ip].append(now)
    return True


# ── Request Models ────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    session_id: Optional[str] = Field(None, max_length=100)
    current_case_id: Optional[str] = Field(None, max_length=50)


class AIRequest(BaseModel):
    system: str = Field(..., min_length=1, max_length=MAX_SYSTEM_PROMPT_LENGTH)
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    max_tokens: int = Field(4096, ge=1, le=16384)
    temperature: float = Field(0.3, ge=0.0, le=1.0)


# ── Demo Cases ────────────────────────────────────
PHASES = [
    "Pre-Suit",
    "Filing",
    "Pleadings",
    "Discovery",
    "Depositions",
    "Experts",
    "Motions",
    "Pre-Trial",
    "Trial",
]
CASES = [
    {
        "id": "c1",
        "name": "Rodriguez v. Smith Trucking",
        "number": "24STCV12345",
        "type": "Personal Injury",
        "client": "Maria Rodriguez",
        "opposing": "Smith Trucking, Inc.",
        "phase": 3,
        "specials": 88000,
        "valuation": {"lo": 150, "mid": 275, "hi": 450},
        "deadline": {
            "date": "Mar 11",
            "text": "45-Day Discovery Motion",
            "urgent": True,
        },
        "modules": {
            "pleadings": {
                "status": "complete",
                "label": "5 COAs filed",
                "detail": "Negligence, MV Neg, Respondeat Superior, Neg Entrustment, Neg Per Se",
            },
            "discovery": {
                "status": "active",
                "label": "5 deficient responses",
                "detail": "M&C letter drafted",
            },
            "trial": {
                "status": "building",
                "label": "Cross: J. Smith (25 Qs)",
                "detail": "6 chapters, 15 source-linked",
            },
            "settlement": {
                "status": "monitoring",
                "label": "Post-discovery trigger",
                "detail": "Reassess after discovery",
            },
        },
    },
    {
        "id": "c2",
        "name": "Chen v. Pacific Properties",
        "number": "25STCV02890",
        "type": "Premises Liability",
        "client": "David Chen",
        "opposing": "Pacific Properties LLC",
        "phase": 2,
        "specials": 34500,
        "valuation": {"lo": 55, "mid": 95, "hi": 165},
        "deadline": {
            "date": "Mar 28",
            "text": "Defendant Response Due",
            "urgent": False,
        },
        "modules": {
            "pleadings": {
                "status": "complete",
                "label": "3 COAs filed",
                "detail": "Premises Liability, Negligence, Breach",
            },
            "discovery": {
                "status": "pending",
                "label": "After answer",
                "detail": "Prepare once defendant answers",
            },
            "settlement": {
                "status": "active",
                "label": "Demand sent: $85K",
                "detail": "Response due Mar 15",
            },
        },
    },
    {
        "id": "c3",
        "name": "Williams v. TechStart",
        "number": None,
        "type": "Employment — FEHA",
        "client": "Angela Williams",
        "opposing": "TechStart Inc.",
        "phase": 1,
        "specials": 128000,
        "valuation": {"lo": 200, "mid": 425, "hi": 750},
        "deadline": {
            "date": "Mar 1",
            "text": "Complete Intake & File",
            "urgent": True,
        },
        "modules": {
            "pleadings": {
                "status": "active",
                "label": "Analyzing 5 COAs",
                "detail": "WT, Discrim, Harassment, Retaliation, Breach",
            },
            "settlement": {
                "status": "assessing",
                "label": "High-value FEHA",
                "detail": "Recommend filing first for leverage",
            },
        },
    },
]


def get_case(cid: str):
    return next((c for c in CASES if c["id"] == cid), None)


# ── CaseCommander System Prompt ───────────────────
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
        urg = (
            f" ⚠️ URGENT: {c['deadline']['text']} ({c['deadline']['date']})"
            if c.get("deadline", {}).get("urgent")
            else ""
        )
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


# ── Claude API (server-side) ─────────────────────
async def call_claude(
    system: str,
    messages: List[Dict],
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> Dict:
    if not API_KEY:
        logger.error("Claude API call attempted without API key")
        return {
            "success": False,
            "text": "",
            "error": "No API key configured. Add ANTHROPIC_API_KEY to .env",
        }

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
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code == 200:
                data = resp.json()
                text = "".join(
                    b.get("text", "")
                    for b in data.get("content", [])
                    if b.get("type") == "text"
                )
                logger.info(
                    "Claude API success: %d input tokens, %d output tokens",
                    data.get("usage", {}).get("input_tokens", 0),
                    data.get("usage", {}).get("output_tokens", 0),
                )
                return {
                    "success": True,
                    "text": text,
                    "usage": data.get("usage", {}),
                }
            if resp.status_code in (429, 529):
                wait = (2**attempt) * 2
                logger.warning(
                    "Claude API rate limited (%d), retrying in %ds (attempt %d/3)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                )
                await asyncio.sleep(wait)
                continue
            logger.error("Claude API error %d: %s", resp.status_code, resp.text[:200])
            return {
                "success": False,
                "text": "",
                "error": f"AI service error (status {resp.status_code})",
            }
        except httpx.TimeoutException:
            logger.warning("Claude API timeout (attempt %d/3)", attempt + 1)
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "text": "", "error": "AI service timeout"}
        except Exception as e:
            logger.exception("Claude API unexpected error (attempt %d/3)", attempt + 1)
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "text": "", "error": "AI service unavailable"}

    return {"success": False, "text": "", "error": "Max retries exceeded"}


# ── Lifespan ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    k = "API key loaded" if API_KEY else "No API key — add to .env"
    port = os.environ.get("PORT", "3000")
    logger.info("CaseCommand Server v2.0 starting")
    logger.info("API key: %s", k)
    logger.info("Model: %s", MODEL)
    logger.info("Listening on http://localhost:%s", port)
    logger.info(
        "Session TTL: %ds, cleanup interval: %ds, max sessions: %d",
        SESSION_TTL_SECONDS,
        SESSION_CLEANUP_INTERVAL,
        MAX_SESSIONS,
    )

    # Start background session cleanup
    cleanup_task = asyncio.create_task(_cleanup_expired_sessions())

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("CaseCommand Server shutting down")


# ── FastAPI ───────────────────────────────────────
app = FastAPI(title="CaseCommand", version="2.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Security headers middleware ───────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ── Request logging middleware ────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "[%s] %s %s → %d (%.0fms)",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── Rate limiting middleware (AI endpoints only) ──
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only rate limit AI-calling endpoints
    if request.url.path in ("/api/chat", "/api/ai", "/api/digest"):
        client_ip = request.client.host if request.client else "unknown"
        if not _check_rate_limit(client_ip):
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )
    return await call_next(request)


# ── Global exception handler ─────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ══════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the CaseCommand UI."""
    base = Path(__file__).parent
    for path in [
        base / "static" / "index.html",
        base / "index.html",
        base / "casecommand-ui.html",
    ]:
        if path.exists():
            return HTMLResponse(content=path.read_text())
    return HTMLResponse(
        "<h1>CaseCommand server running. Place index.html in project root or static/</h1>"
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(API_KEY),
        "model": MODEL,
        "cases": len(CASES),
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/cases")
async def list_cases():
    return {"cases": CASES}


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    c = get_case(case_id)
    if not c:
        raise HTTPException(404, "Case not found")
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
        session["history"].append(
            {"role": "assistant", "content": result["text"]}
        )
        return {
            "response": result["text"],
            "session_id": sid,
            "usage": result.get("usage"),
        }
    else:
        logger.error("Chat failed for session %s: %s", sid, result["error"])
        raise HTTPException(502, result["error"])


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
        return {
            "success": True,
            "text": result["text"],
            "usage": result.get("usage"),
        }
    raise HTTPException(502, result["error"])


@app.get("/api/deadlines")
async def deadlines():
    dl = [
        {"case": c["name"], "case_id": c["id"], **c["deadline"]}
        for c in CASES
        if c.get("deadline")
    ]
    dl.sort(key=lambda d: (not d.get("urgent"), d.get("date", "")))
    return {"deadlines": dl}


@app.get("/api/digest")
async def daily_digest():
    result = await call_claude(
        build_prompt(),
        [
            {
                "role": "user",
                "content": "Generate a concise daily digest: all case statuses, urgent deadlines, pending actions, and recommendations.",
            }
        ],
        max_tokens=2000,
    )
    if result["success"]:
        return {
            "digest": result["text"],
            "generated_at": datetime.now().isoformat(),
        }
    raise HTTPException(502, result.get("error"))


# ══════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("RENDER") is None,
    )
