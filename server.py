"""
CaseCommand Server — FastAPI Application Factory

Unified gateway for web dashboard, Telegram, WhatsApp, and SMS channels.
All channels route through the same Casey agent (src/agent.py).

Modular architecture:
  - src/routes/       — API route modules
  - src/auth/         — JWT authentication
  - src/billing/      — Stripe integration
  - src/storage/      — Document generation & storage
  - src/middleware/    — Rate limiting, usage tracking
  - src/channels/     — Telegram, Twilio adapters
  - src/agent.py      — Unified AI agent engine
  - src/config.py     — Centralized configuration
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from supabase import create_client

from src.config import get_settings
from src.api_client import CaseCommandAI
from src.storage.documents import DocumentStore
from src.middleware.rate_limit import limiter
from src.middleware.usage import UsageTracker
from src.billing.stripe_service import StripeService

# Route modules
from src.routes import (
    auth_routes,
    case_routes,
    chat_routes,
    ai_routes,
    document_routes,
    billing_routes,
    channel_routes,
    agent_lab_routes,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""
    settings = get_settings()

    # Validate critical config
    missing = settings.validate_required()
    if missing:
        logger.warning("Missing env vars: %s", ", ".join(missing))

    app = FastAPI(
        title="CaseCommand API",
        version="2.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    # --- CORS ---
    allowed_origins = [
        settings.BASE_URL,
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    # Filter out empty strings
    allowed_origins = [o for o in allowed_origins if o]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Rate Limiting ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- Shared Services (attached to app.state for route access) ---
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    app.state.supabase = supabase
    app.state.ai_client = CaseCommandAI()
    app.state.doc_store = DocumentStore(supabase_client=supabase)
    app.state.usage_tracker = UsageTracker(supabase)
    app.state.stripe_service = StripeService(supabase) if settings.STRIPE_SECRET_KEY else None

    # --- Register Route Modules ---
    app.include_router(auth_routes.router)
    app.include_router(case_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(ai_routes.router)
    app.include_router(document_routes.router)
    app.include_router(billing_routes.router)
    app.include_router(channel_routes.router)
    app.include_router(agent_lab_routes.router)

    # --- Legacy v0 endpoints (backward compat — will be removed) ---
    _register_legacy_routes(app)

    # --- Frontend ---
    @app.get("/", include_in_schema=False)
    def serve_frontend():
        index_path = Path(__file__).parent / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
        return HTMLResponse(
            "<h1>CaseCommand</h1><p>Visit <a href='/docs'>/docs</a> for the API.</p>"
        )

    # --- Health Check ---
    @app.get("/api/health")
    @app.get("/api/v1/health")
    def health():
        """Health check — verifies core services are reachable."""
        health_status = {
            "status": "ok",
            "version": "2.0.0",
            "model": settings.CLAUDE_MODEL,
            "services": {
                "supabase": bool(settings.SUPABASE_URL),
                "anthropic": bool(settings.ANTHROPIC_API_KEY),
                "stripe": bool(settings.STRIPE_SECRET_KEY),
            },
        }
        return health_status

    return app


def _register_legacy_routes(app: FastAPI):
    """
    Backward-compatible v0 routes that proxy to v1.
    These allow the existing index.html frontend to work unchanged
    while we build the new frontend.
    """
    from fastapi import Depends, HTTPException
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import FileResponse
    from src.models.requests import (
        CaseCreate, ChatRequest, AIRequest,
        DiscoveryRequest, SettlementRequest, OutlineRequest, AgentOutputUpdate,
    )
    from src.agent import process_message
    from src.storage.documents import (
        DocumentStore, extract_title_and_body, title_from_message, LOCAL_DIR, OUTLINES_DIR,
    )
    from src.channels import telegram as tg_channel

    settings = get_settings()
    security = HTTPBearer(auto_error=False)

    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Legacy auth — requires AUTH_TOKEN to be set."""
        if not settings.AUTH_TOKEN:
            # SECURITY FIX: Reject all requests if no auth is configured
            raise HTTPException(status_code=401, detail="Server auth not configured")
        if not credentials or credentials.credentials != settings.AUTH_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid or missing token")

    @app.get("/api/cases")
    def legacy_list_cases(_=Depends(verify_token)):
        db = app.state.supabase
        result = db.table("cases").select("*").execute()
        return result.data

    @app.get("/api/cases/{case_id}")
    def legacy_get_case(case_id: str, _=Depends(verify_token)):
        db = app.state.supabase
        result = db.table("cases").select("*").eq("id", case_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Case not found")
        return result.data[0]

    @app.post("/api/cases", status_code=201)
    def legacy_create_case(case: CaseCreate, _=Depends(verify_token)):
        db = app.state.supabase
        data = {
            "case_name": case.name,
            "case_type": case.type,
            "client_name": case.client,
            "opposing_party": case.opposing,
        }
        result = db.table("cases").insert(data).execute()
        return result.data[0]

    @app.post("/api/chat")
    async def legacy_chat(req: ChatRequest, _=Depends(verify_token)):
        db = app.state.supabase
        doc_store: DocumentStore = app.state.doc_store
        ctx = {"supabase": db}
        response = await process_message(req.message, context=ctx)
        reply_text = response["reply"].strip()
        document = None

        for tool_call in response.get("tool_calls", []):
            if tool_call["name"] == "generate_legal_document":
                try:
                    title = tool_call["input"]["title"]
                    body = tool_call["input"]["body"]
                    filename, _ = doc_store.build_docx(title, body)
                    document = {
                        "filename": filename,
                        "url": f"/api/documents/{filename}",
                        "title": title.replace("_", " "),
                    }
                    if not reply_text:
                        reply_text = body
                except Exception:
                    pass

        if not document and "DOCUMENT_TITLE:" in reply_text:
            try:
                fallback = title_from_message(req.message)
                title, body = extract_title_and_body(reply_text, fallback=fallback)
                filename, _ = doc_store.build_docx(title, body)
                document = {
                    "filename": filename,
                    "url": f"/api/documents/{filename}",
                    "title": title.replace("_", " "),
                }
                reply_text = body
            except Exception:
                pass

        if document:
            reply_text += (
                f"\n\n**Document Ready:** {document['title']}\n"
                f"Download: {document['url']}"
            )

        return {
            "response": reply_text,
            "model": response["model"],
            "document": document,
            "session_id": req.session_id,
        }

    @app.post("/api/ai")
    async def legacy_ai(req: AIRequest, _=Depends(verify_token)):
        ai_client = app.state.ai_client
        try:
            response = ai_client._call_api(req.system, req.message, max_tokens=req.max_tokens)
            return {"text": response["text"], "success": True, "usage": response.get("usage", {})}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/documents/{filename}", include_in_schema=False)
    def legacy_download_document(filename: str, _=Depends(verify_token)):
        safe_filename = Path(filename).name
        filepath = LOCAL_DIR / safe_filename
        if not filepath.exists() or not filepath.is_file():
            raise HTTPException(status_code=404, detail="Document not found")
        return FileResponse(
            str(filepath),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=safe_filename,
        )

    @app.get("/api/deadlines")
    def legacy_deadlines(_=Depends(verify_token)):
        db = app.state.supabase
        result = (
            db.table("cases")
            .select("*")
            .eq("status", "active")
            .order("created_at", desc=False)
            .execute()
        )
        return result.data

    @app.post("/api/discovery")
    def legacy_discovery(req: DiscoveryRequest, _=Depends(verify_token)):
        ai_client = app.state.ai_client
        response = ai_client.analyze_discovery_responses(
            case_name=req.case_name,
            discovery_type=req.discovery_type,
            requests_and_responses=req.requests_and_responses,
        )
        return {"result": response["text"], "model": response["model"]}

    @app.post("/api/settlement")
    def legacy_settlement(req: SettlementRequest, _=Depends(verify_token)):
        ai_client = app.state.ai_client
        response = ai_client.generate_settlement_narrative(
            case_name=req.case_name,
            trigger_point=req.trigger_point,
            valuation_data=req.valuation_data,
            recommendation_data=req.recommendation_data,
        )
        return {"result": response["text"], "model": response["model"]}

    @app.post("/api/outline")
    def legacy_outline(req: OutlineRequest, _=Depends(verify_token)):
        ai_client = app.state.ai_client
        from src.routes.ai_routes import _build_outline_html
        import uuid
        response = ai_client.generate_examination_outline(
            case_name=req.case_name,
            witness_name=req.witness_name,
            witness_role=req.witness_role,
            exam_type=req.exam_type,
            case_documents=req.documents,
            case_theory=req.case_theory,
        )
        html = _build_outline_html(
            case_name=req.case_name,
            witness_name=req.witness_name,
            exam_type=req.exam_type,
            outline_text=response["text"],
        )
        outline_id = uuid.uuid4().hex[:8]
        filename = f"outline_{outline_id}.html"
        (OUTLINES_DIR / filename).write_text(html, encoding="utf-8")
        return {"url": f"/api/outlines/{filename}", "model": response["model"]}

    @app.get("/api/outlines/{filename}", include_in_schema=False)
    def legacy_serve_outline(filename: str):
        safe = Path(filename).name
        filepath = OUTLINES_DIR / safe
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Outline not found")
        return HTMLResponse(content=filepath.read_text(encoding="utf-8"))

    @app.get("/api/agent-outputs")
    def legacy_list_outputs(status: str | None = None, agent: str | None = None, limit: int = 50, _=Depends(verify_token)):
        db = app.state.supabase
        query = db.table("agent_outputs").select("*").order("created_at", desc=True).limit(limit)
        if status:
            query = query.eq("status", status)
        if agent:
            query = query.eq("agent_name", agent)
        return query.execute().data

    @app.get("/api/agent-outputs/summary")
    def legacy_outputs_summary(_=Depends(verify_token)):
        db = app.state.supabase
        data = db.table("agent_outputs").select("id,agent_name,status,priority,run_id,created_at").order("created_at", desc=True).execute().data or []
        pending = [r for r in data if r["status"] == "pending"]
        applied = [r for r in data if r["status"] == "applied"]
        dismissed = [r for r in data if r["status"] == "dismissed"]
        agents = {}
        for r in data:
            name = r["agent_name"]
            if name not in agents:
                agents[name] = {"total": 0, "pending": 0, "applied": 0}
            agents[name]["total"] += 1
            if r["status"] == "pending":
                agents[name]["pending"] += 1
            elif r["status"] == "applied":
                agents[name]["applied"] += 1
        run_ids = list({r["run_id"] for r in data if r.get("run_id")})
        return {"total": len(data), "pending": len(pending), "applied": len(applied), "dismissed": len(dismissed), "agents": agents, "latest_run_id": run_ids[0] if run_ids else None}

    @app.patch("/api/agent-outputs/{output_id}")
    def legacy_update_output(output_id: str, update: AgentOutputUpdate, _=Depends(verify_token)):
        from datetime import datetime, timezone
        db = app.state.supabase
        update_data = {"status": update.status}
        if update.status == "applied":
            update_data["applied_at"] = datetime.now(timezone.utc).isoformat()
            update_data["applied_by"] = "admin"
        result = db.table("agent_outputs").update(update_data).eq("id", output_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Agent output not found")
        return result.data[0]

    @app.get("/api/channels/status")
    async def legacy_channel_status(_=Depends(verify_token)):
        from src.channels import telegram as tg_ch, twilio as tw_ch
        tg_webhook = await tg_ch.get_webhook_info() if tg_ch.is_configured() else None
        tg_bot = await tg_ch.get_bot_info() if tg_ch.is_configured() else None
        webhook_url = ""
        webhook_active = False
        if tg_webhook and tg_webhook.get("ok"):
            r = tg_webhook.get("result", {})
            webhook_url = r.get("url", "")
            webhook_active = bool(webhook_url)
        bot_username = ""
        if tg_bot and tg_bot.get("ok"):
            bot_username = tg_bot.get("result", {}).get("username", "")
        return {
            "telegram": {"configured": tg_ch.is_configured(), "webhook": "/webhook/telegram", "webhook_url": webhook_url, "webhook_active": webhook_active, "bot_username": bot_username},
            "twilio_sms": {"configured": tw_ch.is_configured() and bool(tw_ch.TWILIO_PHONE_NUMBER), "webhook": "/webhook/twilio"},
            "twilio_whatsapp": {"configured": tw_ch.is_configured() and bool(tw_ch.TWILIO_WHATSAPP_NUMBER), "webhook": "/webhook/twilio"},
            "web": {"configured": True, "endpoint": "/api/chat"},
        }

    @app.post("/api/channels/telegram/setup")
    async def legacy_telegram_setup(_=Depends(verify_token)):
        import os
        if not tg_channel.is_configured():
            raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not set")
        base_url = os.environ.get("BASE_URL", "").rstrip("/")
        if not base_url:
            raise HTTPException(status_code=400, detail="BASE_URL not set")
        return await tg_channel.set_webhook(f"{base_url}/webhook/telegram")


# --- App instance ---
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
