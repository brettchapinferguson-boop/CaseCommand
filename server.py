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
import secrets
import httpx

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

import database as db


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

# ── Auth config ───────────────────────────────────
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")
AUTH_ENABLED = AUTH_TOKEN != ""

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

# ── Phase labels ──────────────────────────────────
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
            logger.info(
                "Cleaned up %d expired sessions, %d remaining",
                len(expired),
                len(sessions),
            )


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


# ── Auth dependency ───────────────────────────────
async def verify_auth(request: Request):
    """Verify bearer token if AUTH_TOKEN is configured."""
    if not AUTH_ENABLED:
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header[7:]
    if not secrets.compare_digest(token, AUTH_TOKEN):
        raise HTTPException(401, "Invalid authentication token")


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


class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    number: Optional[str] = Field(None, max_length=50)
    type: str = Field(..., min_length=1, max_length=100)
    client: str = Field(..., min_length=1, max_length=200)
    opposing: str = Field(..., min_length=1, max_length=200)
    phase: int = Field(0, ge=0, le=8)
    specials: int = Field(0, ge=0)
    valuation: Optional[Dict] = None
    deadline: Optional[Dict] = None
    modules: Optional[Dict] = None


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    number: Optional[str] = Field(None, max_length=50)
    type: Optional[str] = Field(None, min_length=1, max_length=100)
    client: Optional[str] = Field(None, min_length=1, max_length=200)
    opposing: Optional[str] = Field(None, min_length=1, max_length=200)
    phase: Optional[int] = Field(None, ge=0, le=8)
    specials: Optional[int] = Field(None, ge=0)
    valuation: Optional[Dict] = None
    deadline: Optional[Dict] = None
    modules: Optional[Dict] = None


# ── CaseCommander System Prompt ───────────────────
async def build_prompt(case: Optional[Dict] = None) -> str:
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    cases = await db.get_all_cases()
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
    for c in cases:
        phase = PHASES[c["phase"]] if c["phase"] < len(PHASES) else "?"
        urg = (
            f" ⚠️ URGENT: {c['deadline']['text']} ({c['deadline']['date']})"
            if c.get("deadline") and c["deadline"].get("urgent")
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


# ── Claude API (server-side, shared client) ───────
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=120)
    return _http_client


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

    client = _get_http_client()

    for attempt in range(3):
        try:
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
            logger.error(
                "Claude API error %d: %s", resp.status_code, resp.text[:200]
            )
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
            logger.exception(
                "Claude API unexpected error (attempt %d/3)", attempt + 1
            )
            if attempt < 2:
                await asyncio.sleep(1)
                continue
            return {"success": False, "text": "", "error": "AI service unavailable"}

    return {"success": False, "text": "", "error": "Max retries exceeded"}


# ── UI cache ──────────────────────────────────────
_cached_ui: Optional[str] = None


def _load_ui() -> Optional[str]:
    """Load the UI HTML file once."""
    global _cached_ui
    base = Path(__file__).parent
    for path in [
        base / "static" / "index.html",
        base / "index.html",
        base / "casecommand-ui.html",
    ]:
        if path.exists():
            _cached_ui = path.read_text()
            logger.info("Loaded UI from %s", path)
            return _cached_ui
    logger.warning("No UI file found")
    return None


# ── Lifespan ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    k = "API key loaded" if API_KEY else "No API key — add to .env"
    port = os.environ.get("PORT", "3000")
    logger.info("CaseCommand Server v2.0 starting")
    logger.info("API key: %s", k)
    logger.info("Model: %s", MODEL)
    logger.info(
        "Auth: %s",
        "enabled" if AUTH_ENABLED else "disabled (set AUTH_TOKEN to enable)",
    )
    logger.info("Listening on http://localhost:%s", port)
    logger.info(
        "Session TTL: %ds, cleanup interval: %ds, max sessions: %d",
        SESSION_TTL_SECONDS,
        SESSION_CLEANUP_INTERVAL,
        MAX_SESSIONS,
    )

    # Initialize database
    await db.init_db()
    logger.info("Database initialized at %s", db.DB_PATH)

    # Load UI into memory
    _load_ui()

    # Start background session cleanup
    cleanup_task = asyncio.create_task(_cleanup_expired_sessions())

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Close shared HTTP client
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

    logger.info("CaseCommand Server shutting down")


# ── FastAPI ───────────────────────────────────────
app = FastAPI(title="CaseCommand", version="2.0", lifespan=lifespan)

# GZip compression (responses > 500 bytes)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
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
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
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
        client_ip = _get_client_ip(request)
        if not _check_rate_limit(client_ip):
            logger.warning(
                "Rate limit exceeded for %s on %s", client_ip, request.url.path
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later."
                },
            )
    return await call_next(request)


def _get_client_ip(request: Request) -> str:
    """Get client IP, checking trusted proxy headers first."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# ── Global exception handler ─────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ══════════════════════════════════════════════════
# ROUTES — Public
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the CaseCommand UI."""
    if _cached_ui:
        return HTMLResponse(content=_cached_ui)
    return HTMLResponse(
        "<h1>CaseCommand server running. Place index.html in project root or static/</h1>"
    )


@app.get("/api/health")
async def health():
    case_count = await db.get_case_count()
    return {
        "status": "ok",
        "api_key_configured": bool(API_KEY),
        "auth_enabled": AUTH_ENABLED,
        "model": MODEL,
        "cases": case_count,
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════
# ROUTES — Protected (auth required if AUTH_TOKEN set)
# ══════════════════════════════════════════════════

@app.get("/api/cases", dependencies=[Depends(verify_auth)])
async def list_cases():
    cases = await db.get_all_cases()
    return {"cases": cases}


@app.get("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def get_case_detail(case_id: str):
    c = await db.get_case(case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    return c


@app.post("/api/cases", dependencies=[Depends(verify_auth)], status_code=201)
async def create_case(req: CaseCreate):
    """Create a new case."""
    case_data = req.model_dump(exclude_none=True)
    case_data["id"] = str(uuid.uuid4())[:8]
    if "valuation" not in case_data:
        case_data["valuation"] = {"lo": 0, "mid": 0, "hi": 0}
    created = await db.create_case(case_data)
    logger.info("Case created: %s (%s)", created["name"], created["id"])
    return created


@app.put("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def update_case(case_id: str, req: CaseUpdate):
    """Update an existing case."""
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updated = await db.update_case(case_id, updates)
    if not updated:
        raise HTTPException(404, "Case not found")
    logger.info("Case updated: %s (%s)", updated["name"], updated["id"])
    return updated


@app.delete("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def delete_case(case_id: str):
    """Delete a case."""
    deleted = await db.delete_case(case_id)
    if not deleted:
        raise HTTPException(404, "Case not found")
    logger.info("Case deleted: %s", case_id)
    return {"deleted": True, "id": case_id}


@app.post("/api/chat", dependencies=[Depends(verify_auth)])
async def commander_chat(req: ChatRequest):
    """CaseCommander multi-turn chat with session tracking."""
    sid = req.session_id or str(uuid.uuid4())
    session = get_session(sid)

    case = (await db.get_case(req.current_case_id)) if req.current_case_id else None
    system = await build_prompt(case)

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


@app.post("/api/ai", dependencies=[Depends(verify_auth)])
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


@app.get("/api/deadlines", dependencies=[Depends(verify_auth)])
async def deadlines():
    cases = await db.get_all_cases()
    dl = [
        {"case": c["name"], "case_id": c["id"], **c["deadline"]}
        for c in cases
        if c.get("deadline")
    ]
    dl.sort(key=lambda d: (not d.get("urgent"), d.get("date", "")))
    return {"deadlines": dl}


@app.get("/api/digest", dependencies=[Depends(verify_auth)])
async def daily_digest():
    result = await call_claude(
        await build_prompt(),
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
        forwarded_allow_ips="*",
    )
