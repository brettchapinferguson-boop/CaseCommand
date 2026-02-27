"""
CaseCommand v2.0 - FastAPI Server
Main API with document upload, case management, and agentic chat.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import get_settings
from database import CaseDB
from document_pipeline import (
    extract_text_from_pdf,
    process_document_for_new_case,
    process_document_for_existing_case,
)
from agent import chat as agent_chat

app = FastAPI(title="CaseCommand v2.0", version="2.0.0")

# Lazy-init: avoid crashing at import time if env vars not yet available
_db = None
_settings = None

def get_db():
    global _db
    if _db is None:
        _db = CaseDB()
    return _db

def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ──────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    case_id: Optional[str] = None

class ProcessDocRequest(BaseModel):
    document_id: str
    case_id: Optional[str] = None  # None = create new case
    
class ActionApprovalRequest(BaseModel):
    action_id: str
    approved: bool
    rejection_reason: Optional[str] = None

class CaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    case_type: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    trial_date: Optional[str] = None
    next_deadline: Optional[str] = None
    next_deadline_description: Optional[str] = None


# ── Auth Helper ──────────────────────────────────────────────
# For MVP, we use a simple user_id header. In production, use Supabase JWT.

def get_user_id(request: Request) -> str:
    """Extract user_id from request. MVP: header. Production: JWT."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        # Default user for development
        user_id = "00000000-0000-0000-0000-000000000001"
    return user_id


# ── Document Upload ──────────────────────────────────────────

@app.post("/api/v2/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
):
    """
    Upload a document. If case_id is provided, adds to that case.
    If not, the document is stored as unassigned for later processing.
    """
    user_id = get_user_id(request)
    
    # Validate file
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    file_bytes = await file.read()
    settings = _get_settings()
    if len(file_bytes) > settings.max_upload_size:
        raise HTTPException(400, f"File too large. Max {settings.max_upload_size // 1024 // 1024}MB")
    
    # Extract text from PDF
    extracted_text = ""
    page_count = 0
    
    if file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf"):
        try:
            extraction = extract_text_from_pdf(file_bytes)
            extracted_text = extraction["full_text"]
            page_count = extraction["page_count"]
        except Exception as e:
            raise HTTPException(400, f"Could not process PDF: {str(e)}")
    elif file.filename.lower().endswith((".txt", ".md")):
        extracted_text = file_bytes.decode("utf-8", errors="replace")
        page_count = 1
    
    # Upload to Supabase Storage
    try:
        file_path = get_db().upload_file(user_id, file.filename, file_bytes, file.content_type or "application/octet-stream")
    except Exception as e:
        # If storage fails, still create the record with text
        file_path = f"local/{user_id}/{file.filename}"
    
    # Create document record
    doc_data = {
        "user_id": user_id,
        "case_id": case_id,
        "filename": file.filename,
        "file_path": file_path,
        "file_size": len(file_bytes),
        "file_type": file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown",
        "mime_type": file.content_type,
        "extracted_text": extracted_text,
        "page_count": page_count,
        "processing_status": "pending"
    }
    
    doc = get_db().create_document(doc_data)
    
    return {
        "success": True,
        "document": {
            "id": doc["id"],
            "filename": doc["filename"],
            "page_count": page_count,
            "text_length": len(extracted_text),
            "processing_status": "pending",
            "case_id": case_id
        },
        "message": "Document uploaded. Ready for processing."
    }


@app.post("/api/v2/documents/process")
async def process_document(request: Request, body: ProcessDocRequest):
    """
    Process an uploaded document: analyze with AI and create/update case.
    """
    user_id = get_user_id(request)
    
    try:
        if body.case_id:
            # Add to existing case
            result = process_document_for_existing_case(body.document_id, body.case_id, user_id)
            return {
                "success": True,
                "action": "added_to_case",
                "case": result["case"],
                "new_facts": result["new_facts_count"],
                "new_timeline_events": result["new_timeline_count"],
                "message": f"Document processed and added to case '{result['case']['name']}'"
            }
        else:
            # Create new case
            result = process_document_for_new_case(body.document_id, user_id)
            return {
                "success": True,
                "action": "new_case_created",
                "case": result["case"],
                "facts_extracted": result["facts_count"],
                "timeline_events": result["timeline_count"],
                "message": f"New case '{result['case']['name']}' created with full analysis"
            }
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ── Case Management ──────────────────────────────────────────

@app.get("/api/v2/cases")
async def list_cases(request: Request, status: Optional[str] = None):
    user_id = get_user_id(request)
    cases = get_db().get_cases(user_id, status)
    return {"success": True, "cases": cases}


@app.get("/api/v2/cases/{case_id}")
async def get_case(request: Request, case_id: str):
    user_id = get_user_id(request)
    db = get_db()
    case = db.get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    documents = db.get_documents(case_id)
    facts = db.get_facts(case_id)
    timeline = db.get_timeline(case_id)
    
    return {
        "success": True,
        "case": case,
        "documents": documents,
        "facts": facts,
        "timeline": timeline,
        "stats": {
            "total_documents": len(documents),
            "total_facts": len(facts),
            "timeline_events": len(timeline),
            "liability_facts": len([f for f in facts if f.get("category") == "liability"]),
            "damages_facts": len([f for f in facts if f.get("category") == "damages"]),
        }
    }


@app.patch("/api/v2/cases/{case_id}")
async def update_case(request: Request, case_id: str, body: CaseUpdateRequest):
    user_id = get_user_id(request)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "No fields to update")
    
    case = get_db().update_case(case_id, update_data)
    return {"success": True, "case": case}


@app.get("/api/v2/cases/{case_id}/documents")
async def get_case_documents(request: Request, case_id: str):
    documents = get_db().get_documents(case_id)
    return {"success": True, "documents": documents}


@app.get("/api/v2/cases/{case_id}/facts")
async def get_case_facts(request: Request, case_id: str, category: Optional[str] = None):
    facts = get_db().get_facts(case_id, category)
    return {"success": True, "facts": facts}


@app.get("/api/v2/cases/{case_id}/timeline")
async def get_case_timeline(request: Request, case_id: str):
    timeline = get_db().get_timeline(case_id)
    return {"success": True, "timeline": timeline}


# ── Agentic Chat ─────────────────────────────────────────────

@app.post("/api/v2/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    user_id = get_user_id(request)
    session_id = body.session_id or str(uuid.uuid4())
    
    try:
        result = agent_chat(
            user_message=body.message,
            user_id=user_id,
            session_id=session_id,
            case_id=body.case_id
        )
        return {
            "success": True,
            "response": result["response"],
            "actions": result["actions"],
            "session_id": result["session_id"]
        }
    except Exception as e:
        raise HTTPException(500, f"Chat error: {str(e)}")


@app.get("/api/v2/chat/history/{session_id}")
async def get_chat_history(request: Request, session_id: str):
    history = get_db().get_conversation(session_id)
    return {"success": True, "messages": history}


# ── Action Approval ──────────────────────────────────────────

@app.get("/api/v2/actions/pending")
async def get_pending_actions(request: Request):
    user_id = get_user_id(request)
    actions = get_db().get_pending_actions(user_id)
    return {"success": True, "actions": actions}


@app.post("/api/v2/actions/approve")
async def approve_action(request: Request, body: ActionApprovalRequest):
    user_id = get_user_id(request)
    db = get_db()

    if body.approved:
        action = db.approve_action(body.action_id, user_id)
        # TODO: Execute the actual action (send email, create calendar event)
        # This will be wired to n8n in Phase 3
        return {"success": True, "message": "Action approved", "action": action}
    else:
        action = db.reject_action(body.action_id, body.rejection_reason or "Rejected by user")
        return {"success": True, "message": "Action rejected", "action": action}


# ── Dashboard Stats ──────────────────────────────────────────

@app.get("/api/v2/dashboard")
async def get_dashboard(request: Request):
    user_id = get_user_id(request)
    db = get_db()
    cases = db.get_cases(user_id)
    pending_actions = db.get_pending_actions(user_id)
    
    active_cases = [c for c in cases if c.get("status") in ("active", "discovery", "trial_prep", "trial")]
    
    # Find upcoming deadlines
    upcoming_deadlines = []
    for case in active_cases:
        if case.get("next_deadline"):
            upcoming_deadlines.append({
                "case_name": case["name"],
                "case_id": case["id"],
                "deadline": case["next_deadline"],
                "description": case.get("next_deadline_description", "")
            })
    
    return {
        "success": True,
        "stats": {
            "total_cases": len(cases),
            "active_cases": len(active_cases),
            "pending_actions": len(pending_actions),
            "upcoming_deadlines": len(upcoming_deadlines)
        },
        "recent_cases": cases[:5],
        "pending_actions": pending_actions[:5],
        "upcoming_deadlines": sorted(upcoming_deadlines, key=lambda x: x.get("deadline", ""))[:5]
    }


# ── Health Check ─────────────────────────────────────────────

@app.get("/api/v2/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.1",
        "service": "CaseCommand v2.0",
        "frontend_loaded": _index_html_content is not None,
    }


# ── Static Files (Frontend) ──────────────────────────────────

# Try multiple possible locations for index.html
_index_html_content = None
_search_paths = [
    Path(__file__).parent / "static" / "index.html",
    Path("/app/static/index.html"),
    Path.cwd() / "static" / "index.html",
]
for _p in _search_paths:
    if _p.exists():
        _index_html_content = _p.read_text()
        break

static_dir = Path(__file__).parent / "static"


@app.get("/")
async def serve_root():
    if _index_html_content:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=_index_html_content)
    return JSONResponse({
        "status": "running",
        "version": "2.0.0",
        "docs": "/docs",
        "note": "Frontend not found. API is running.",
        "searched": [str(p) + " exists=" + str(p.exists()) for p in _search_paths],
    })


# Mount static files for any other assets (CSS, JS, images)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
