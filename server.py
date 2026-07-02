"""
CaseCommand Production Server
==============================
AI litigation practice server: agentic CaseCommander chat, autonomous
background paralegal, attorney review queue, and California deadline engine.

Setup:
  1. cp .env.example .env
  2. Add your ANTHROPIC_API_KEY to .env
  3. pip install -r requirements.txt
  4. python server.py

Then open http://localhost:3000 (UI) and http://localhost:3000/admin
(paralegal dashboard / review queue).
"""

import os
import json
import uuid
import time
import logging
import asyncio
import secrets

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

import database as db
import worker
import rules
from agent import run_agent, build_commander_prompt
from claude_client import call_claude, close_http_client, MODEL, WORKER_MODEL, API_KEY


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
AI_ENDPOINTS = ("/api/chat", "/api/ai", "/api/digest",
                "/api/agent/cycle", "/api/agent/draft")

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
    if not sessions:
        return
    oldest_sid = min(sessions, key=lambda s: sessions[s].get("last_accessed", 0))
    del sessions[oldest_sid]
    logger.info("Evicted oldest session %s (at capacity %d)", oldest_sid, MAX_SESSIONS)


async def _cleanup_expired_sessions():
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        now = time.time()
        expired = [
            sid for sid, s in sessions.items()
            if now - s.get("last_accessed", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions, %d remaining",
                        len(expired), len(sessions))


# ── Rate Limiting ─────────────────────────────────
def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    if client_ip not in rate_limits:
        rate_limits[client_ip] = []
    rate_limits[client_ip] = [
        t for t in rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(rate_limits[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False
    rate_limits[client_ip].append(now)
    return True


# ── Auth dependency ───────────────────────────────
async def verify_auth(request: Request):
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


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    detail: str = Field("", max_length=5000)
    case_id: Optional[str] = Field(None, max_length=50)
    priority: str = Field("medium", pattern="^(urgent|high|medium|low)$")
    due_date: Optional[str] = Field(None, max_length=10)


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|done|dismissed)$")


class DeadlineCreate(BaseModel):
    case_id: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=300)
    due_date: str = Field(..., min_length=10, max_length=10)
    rule: str = Field("", max_length=200)
    note: str = Field("", max_length=1000)


class ReviewAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    note: str = Field("", max_length=2000)


class DraftRequest(BaseModel):
    case_id: Optional[str] = Field(None, max_length=50)
    doc_type: str = Field(..., max_length=50)
    instructions: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ComputeDeadlinesRequest(BaseModel):
    trigger_event: str = Field(..., max_length=60)
    event_date: str = Field(..., min_length=10, max_length=10)
    service_method: str = Field("personal", max_length=20)


# ── UI cache ──────────────────────────────────────
_cached_ui: Optional[str] = None
_cached_admin: Optional[str] = None


def _load_ui():
    global _cached_ui, _cached_admin
    base = Path(__file__).parent
    for path in [base / "static" / "index.html", base / "index.html",
                 base / "casecommand-ui.html"]:
        if path.exists():
            _cached_ui = path.read_text()
            logger.info("Loaded UI from %s", path)
            break
    else:
        logger.warning("No UI file found")
    admin_path = base / "static" / "admin.html"
    if admin_path.exists():
        _cached_admin = admin_path.read_text()
        logger.info("Loaded admin dashboard from %s", admin_path)


# ── Lifespan ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    port = os.environ.get("PORT", "3000")
    logger.info("CaseCommand Server v3.0 starting")
    logger.info("API key: %s", "loaded" if API_KEY else "MISSING — add to .env")
    logger.info("Models: chat/draft=%s worker=%s", MODEL, WORKER_MODEL)
    logger.info("Auth: %s", "enabled" if AUTH_ENABLED else "disabled (set AUTH_TOKEN)")
    logger.info("Paralegal worker: %s",
                f"every {worker.PARALEGAL_INTERVAL}s" if worker.PARALEGAL_INTERVAL > 0
                else "disabled")
    logger.info("Listening on http://localhost:%s", port)

    await db.init_db()
    logger.info("Database initialized at %s", db.DB_PATH)
    _load_ui()

    cleanup_task = asyncio.create_task(_cleanup_expired_sessions())
    worker.start()

    yield

    await worker.stop()
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_http_client()
    logger.info("CaseCommand Server shutting down")


# ── FastAPI ───────────────────────────────────────
app = FastAPI(title="CaseCommand", version="3.0", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info("[%s] %s %s → %d (%.0fms)", request_id, request.method,
                request.url.path, response.status_code, duration_ms)
    response.headers["X-Request-ID"] = request_id
    return response


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in AI_ENDPOINTS:
        client_ip = _get_client_ip(request)
        if not _check_rate_limit(client_ip):
            logger.warning("Rate limit exceeded for %s on %s",
                           client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )
    return await call_next(request)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ══════════════════════════════════════════════════
# ROUTES — Public
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    if _cached_ui:
        return HTMLResponse(content=_cached_ui)
    return HTMLResponse(
        "<h1>CaseCommand server running. Place index.html in project root or static/</h1>"
    )


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Paralegal dashboard: review queue, tasks, deadlines, agent runs."""
    if _cached_admin:
        return HTMLResponse(content=_cached_admin)
    return HTMLResponse("<h1>Admin dashboard not found (static/admin.html)</h1>")


@app.get("/api/health")
async def health():
    case_count = await db.get_case_count()
    return {
        "status": "ok",
        "api_key_configured": bool(API_KEY),
        "auth_enabled": AUTH_ENABLED,
        "model": MODEL,
        "worker_model": WORKER_MODEL,
        "cases": case_count,
        "active_sessions": len(sessions),
        "paralegal": {
            "enabled": worker.state["enabled"],
            "running": worker.state["running"],
            "last_cycle_at": worker.state["last_cycle_at"],
            "cycles_completed": worker.state["cycles_completed"],
        },
        "timestamp": datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════
# ROUTES — Cases
# ══════════════════════════════════════════════════

@app.get("/api/cases", dependencies=[Depends(verify_auth)])
async def list_cases():
    return {"cases": await db.get_all_cases()}


@app.get("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def get_case_detail(case_id: str):
    c = await db.get_case(case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    return c


@app.post("/api/cases", dependencies=[Depends(verify_auth)], status_code=201)
async def create_case(req: CaseCreate):
    case_data = req.model_dump(exclude_none=True)
    case_data["id"] = str(uuid.uuid4())[:8]
    if "valuation" not in case_data:
        case_data["valuation"] = {"lo": 0, "mid": 0, "hi": 0}
    created = await db.create_case(case_data)
    await db.log_audit("human", "create_case", "case", created["id"], created["name"])
    logger.info("Case created: %s (%s)", created["name"], created["id"])
    return created


@app.put("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def update_case(case_id: str, req: CaseUpdate):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updated = await db.update_case(case_id, updates)
    if not updated:
        raise HTTPException(404, "Case not found")
    await db.log_audit("human", "update_case", "case", case_id, json.dumps(updates, default=str))
    return updated


@app.delete("/api/cases/{case_id}", dependencies=[Depends(verify_auth)])
async def delete_case(case_id: str):
    deleted = await db.delete_case(case_id)
    if not deleted:
        raise HTTPException(404, "Case not found")
    await db.log_audit("human", "delete_case", "case", case_id)
    return {"deleted": True, "id": case_id}


# ══════════════════════════════════════════════════
# ROUTES — Agentic AI
# ══════════════════════════════════════════════════

@app.post("/api/chat", dependencies=[Depends(verify_auth)])
async def commander_chat(req: ChatRequest):
    """CaseCommander agentic chat: multi-turn, with tools — the agent can
    update cases, calendar deadlines, create tasks, and draft documents
    (into the review queue) during the conversation."""
    sid = req.session_id or str(uuid.uuid4())
    session = get_session(sid)

    case = (await db.get_case(req.current_case_id)) if req.current_case_id else None
    system = await build_commander_prompt(case)

    session["history"].append({"role": "user", "content": req.message})

    result = await run_agent(system, session["history"], actor="agent:commander")

    if result["success"]:
        session["history"].append({"role": "assistant", "content": result["text"]})
        return {
            "response": result["text"],
            "session_id": sid,
            "actions": result["actions"],
            "usage": result.get("usage"),
        }
    logger.error("Chat failed for session %s: %s", sid, result["error"])
    raise HTTPException(502, result["error"])


@app.post("/api/ai", dependencies=[Depends(verify_auth)])
async def generic_ai(req: AIRequest):
    """Generic AI endpoint — any module sends system + message, gets response.
    (Kept for the bundled UI's module features.)"""
    result = await call_claude(
        req.system,
        [{"role": "user", "content": req.message}],
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    if result["success"]:
        return {"success": True, "text": result["text"], "usage": result.get("usage")}
    raise HTTPException(502, result["error"])


@app.post("/api/agent/cycle", dependencies=[Depends(verify_auth)])
async def trigger_cycle():
    """Manually trigger a paralegal cycle (also runs on schedule)."""
    if worker.state["running"]:
        raise HTTPException(409, "A paralegal cycle is already running")
    result = await worker.run_cycle(kind="manual_cycle")
    return result


@app.post("/api/agent/draft", dependencies=[Depends(verify_auth)])
async def agent_draft(req: DraftRequest):
    """Ask the agent to draft a specific document into the review queue."""
    case = (await db.get_case(req.case_id)) if req.case_id else None
    if req.case_id and not case:
        raise HTTPException(404, "Case not found")
    system = await build_commander_prompt(case)
    instruction = (
        f"Draft the following document now ({req.doc_type}). Produce the "
        f"COMPLETE document and save it with save_document"
        + (f" for case {req.case_id}" if req.case_id else "")
        + f".\n\nInstructions: {req.instructions}"
    )
    result = await run_agent(
        system, [{"role": "user", "content": instruction}],
        actor="agent:drafter", max_tokens=16384,
    )
    if not result["success"]:
        raise HTTPException(502, result["error"])
    return {
        "summary": result["text"],
        "actions": result["actions"],
        "usage": result["usage"],
        "note": "Draft saved to attorney review queue (if save_document appears in actions)",
    }


@app.get("/api/agent/runs", dependencies=[Depends(verify_auth)])
async def agent_runs(limit: int = 20):
    return {"runs": await db.list_agent_runs(limit=min(limit, 100))}


# ══════════════════════════════════════════════════
# ROUTES — Tasks
# ══════════════════════════════════════════════════

@app.get("/api/tasks", dependencies=[Depends(verify_auth)])
async def get_tasks(status: Optional[str] = None, case_id: Optional[str] = None):
    return {"tasks": await db.list_tasks(status=status, case_id=case_id)}


@app.post("/api/tasks", dependencies=[Depends(verify_auth)], status_code=201)
async def add_task(req: TaskCreate):
    task = await db.create_task({
        "id": str(uuid.uuid4())[:8],
        **req.model_dump(exclude_none=True),
        "created_by": "human",
    })
    await db.log_audit("human", "create_task", "task", task["id"], task["title"])
    return task


@app.patch("/api/tasks/{task_id}", dependencies=[Depends(verify_auth)])
async def set_task_status(task_id: str, req: TaskStatusUpdate):
    task = await db.update_task_status(task_id, req.status)
    if not task:
        raise HTTPException(404, "Task not found")
    await db.log_audit("human", "update_task", "task", task_id, req.status)
    return task


# ══════════════════════════════════════════════════
# ROUTES — Deadlines
# ══════════════════════════════════════════════════

@app.get("/api/deadlines", dependencies=[Depends(verify_auth)])
async def deadlines(within_days: Optional[int] = None):
    """Date-typed deadlines from the deadline engine, soonest first."""
    dls = await db.list_deadlines(within_days=within_days)
    cases = {c["id"]: c["name"] for c in await db.get_all_cases()}
    for d in dls:
        d["case"] = cases.get(d["case_id"], d["case_id"])
    return {"deadlines": dls}


@app.post("/api/deadlines", dependencies=[Depends(verify_auth)], status_code=201)
async def add_deadline(req: DeadlineCreate):
    dl = await db.create_deadline({
        "id": str(uuid.uuid4())[:8],
        **req.model_dump(),
        "created_by": "human",
    })
    await db.log_audit("human", "add_deadline", "deadline", dl["id"],
                       f"{dl['title']} due {dl['due_date']}")
    return dl


@app.post("/api/deadlines/compute", dependencies=[Depends(verify_auth)])
async def compute_deadlines_endpoint(req: ComputeDeadlinesRequest):
    """Compute CA deadlines from a trigger event (does not save)."""
    from datetime import date as _date
    try:
        event_date = _date.fromisoformat(req.event_date)
        computed = rules.compute_deadlines(req.trigger_event, event_date,
                                           req.service_method)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "deadlines": computed,
        "trigger_events": rules.TRIGGER_EVENTS,
        "warning": "Computed dates require attorney verification against local rules",
    }


# ══════════════════════════════════════════════════
# ROUTES — Documents & Attorney Review Queue
# ══════════════════════════════════════════════════

@app.get("/api/documents", dependencies=[Depends(verify_auth)])
async def get_documents(status: Optional[str] = None, case_id: Optional[str] = None):
    docs = await db.list_documents(status=status, case_id=case_id)
    for d in docs:
        d["preview"] = d["content"][:200]
        del d["content"]
    return {"documents": docs}


@app.get("/api/documents/{doc_id}", dependencies=[Depends(verify_auth)])
async def get_document(doc_id: str):
    doc = await db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@app.post("/api/documents/{doc_id}/review", dependencies=[Depends(verify_auth)])
async def review_document(doc_id: str, req: ReviewAction):
    """Attorney review gate: approve or reject AI work product.
    This is the required human-in-the-loop step (RPC 5.3 / ABA Op. 512 /
    proposed CA RPC 1.1 verification duty)."""
    status = "approved" if req.action == "approve" else "rejected"
    doc = await db.review_document(doc_id, status, req.note)
    if not doc:
        raise HTTPException(404, "Document not found")
    await db.log_audit("human:attorney", f"{req.action}_document", "document",
                       doc_id, req.note or doc["title"])
    return doc


@app.get("/api/review/queue", dependencies=[Depends(verify_auth)])
async def review_queue():
    """Everything awaiting the attorney: pending documents + urgent tasks."""
    docs = await db.list_documents(status="pending_review")
    for d in docs:
        d["preview"] = d["content"][:200]
        del d["content"]
    tasks = await db.list_tasks(status="open")
    urgent = [t for t in tasks if t["priority"] in ("urgent", "high")]
    upcoming = await db.list_deadlines(within_days=14)
    return {
        "pending_documents": docs,
        "urgent_tasks": urgent,
        "deadlines_14_days": upcoming,
        "counts": {
            "pending_documents": len(docs),
            "urgent_tasks": len(urgent),
            "open_tasks": len(tasks),
            "deadlines_14_days": len(upcoming),
        },
    }


# ══════════════════════════════════════════════════
# ROUTES — Audit trail (RPC 5.3 supervision record)
# ══════════════════════════════════════════════════

@app.get("/api/audit", dependencies=[Depends(verify_auth)])
async def audit_trail(limit: int = 100):
    return {"audit": await db.list_audit(limit=min(limit, 500))}


# ══════════════════════════════════════════════════
# ROUTES — Digest (kept for the bundled UI)
# ══════════════════════════════════════════════════

@app.get("/api/digest", dependencies=[Depends(verify_auth)])
async def daily_digest():
    system = await build_commander_prompt()
    result = await call_claude(
        system,
        [{"role": "user", "content":
          "Generate a concise daily digest: all case statuses, urgent deadlines, "
          "pending actions, and recommendations."}],
        max_tokens=2000,
    )
    if result["success"]:
        return {"digest": result["text"], "generated_at": datetime.now().isoformat()}
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
