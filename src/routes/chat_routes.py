"""
CaseCommand — Chat Routes

Web dashboard chat endpoint + conversation persistence.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from src.models.requests import ChatRequest
from src.auth.jwt import CurrentUser
from src.agent import process_message
from src.storage.documents import DocumentStore, extract_title_and_body, title_from_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest, user: CurrentUser, request: Request):
    """Web dashboard chat -- routes through the unified Casey agent."""
    db = request.app.state.supabase
    doc_store: DocumentStore = request.app.state.doc_store

    session_id = req.session_id or str(uuid.uuid4())

    # Load conversation history for this session
    history = await _load_history(db, session_id, limit=20)

    # Load firm config for personalized system prompt
    firm_config = None
    if user.org_id:
        try:
            result = db.table("firm_config").select("*").eq("org_id", user.org_id).execute()
            if result.data:
                firm_config = result.data[0]
        except Exception:
            pass

    # Process through agent
    ctx = {
        "supabase": db,
        "org_id": user.org_id,
        "user_id": user.user_id,
        "firm_config": firm_config,
    }
    response = await process_message(
        req.message,
        conversation_history=history,
        context=ctx,
    )
    reply_text, document = _handle_agent_response(response, req.message, doc_store, user.org_id)

    # Persist conversation
    await _save_message(db, session_id, "user", req.message, user.user_id, user.org_id)
    await _save_message(db, session_id, "assistant", reply_text, user.user_id, user.org_id)

    # Track usage
    usage_tracker = request.app.state.usage_tracker
    if usage_tracker and user.org_id:
        tokens = response.get("usage", {}).get("input_tokens", 0) + response.get("usage", {}).get("output_tokens", 0)
        await usage_tracker.record_ai_call(user.org_id, tokens)

    return {
        "response": reply_text,
        "model": response["model"],
        "document": document,
        "session_id": session_id,
    }


@router.get("/history/{session_id}")
async def get_history(session_id: str, user: CurrentUser, request: Request):
    """Get conversation history for a session."""
    db = request.app.state.supabase
    history = await _load_history(db, session_id, limit=100, org_id=user.org_id)
    return {"session_id": session_id, "messages": history}


@router.get("/sessions")
async def list_sessions(user: CurrentUser, request: Request):
    """List recent chat sessions for the current user."""
    db = request.app.state.supabase

    query = (
        db.table("conversation_messages")
        .select("session_id, created_at, content")
        .eq("role", "user")
    )
    if user.org_id:
        query = query.eq("org_id", user.org_id)
    else:
        query = query.eq("sender_id", user.user_id)

    result = query.order("created_at", desc=True).limit(50).execute()

    # Group by session, take first message as preview
    sessions = {}
    for msg in (result.data or []):
        sid = msg["session_id"]
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "preview": msg["content"][:100],
                "created_at": msg["created_at"],
            }

    return list(sessions.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_history(
    db, session_id: str, limit: int = 20, org_id: str | None = None
) -> list[dict]:
    """Load conversation history from the database."""
    try:
        query = (
            db.table("conversation_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(limit)
        )
        result = query.execute()
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in (result.data or [])
        ]
    except Exception as e:
        logger.warning("Failed to load history: %s", e)
        return []


async def _save_message(
    db, session_id: str, role: str, content: str,
    user_id: str | None = None, org_id: str | None = None,
):
    """Persist a message to the conversation_messages table."""
    try:
        db.table("conversation_messages").insert({
            "session_id": session_id,
            "channel": "web",
            "sender_id": user_id,
            "org_id": org_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning("Failed to save message: %s", e)


def _handle_agent_response(
    response: dict, original_message: str, doc_store: DocumentStore, org_id: str | None
) -> tuple[str, dict | None]:
    """Post-process agent response: build .docx if needed."""
    reply_text = response["reply"].strip()
    document = None

    for tool_call in response.get("tool_calls", []):
        if tool_call["name"] == "generate_legal_document":
            try:
                title = tool_call["input"]["title"]
                body = tool_call["input"]["body"]
                filename, local_path = doc_store.build_docx(title, body, org_id)
                document = {
                    "filename": filename,
                    "url": f"/api/v1/documents/{filename}",
                    "title": title.replace("_", " "),
                }
                if not reply_text:
                    reply_text = body
            except Exception:
                pass

    if not document and "DOCUMENT_TITLE:" in reply_text:
        try:
            fallback = title_from_message(original_message)
            title, body = extract_title_and_body(reply_text, fallback=fallback)
            filename, local_path = doc_store.build_docx(title, body, org_id)
            document = {
                "filename": filename,
                "url": f"/api/v1/documents/{filename}",
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

    return reply_text, document
