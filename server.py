"""
CaseCommand Server — FastAPI app on port 3000
"""

import os
import re
import uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from docx import Document as DocxDocument
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import uvicorn

from src.api_client import CaseCommandAI

app = FastAPI(title="CaseCommand API")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
ai_client = CaseCommandAI()

# ---------------------------------------------------------------------------
# Document storage
# ---------------------------------------------------------------------------

DOCUMENTS_DIR = Path(__file__).parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not AUTH_TOKEN:
        return
    if not credentials or credentials.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CaseCreate(BaseModel):
    name: str
    type: str
    client: str
    opposing: str


class ChatRequest(BaseModel):
    message: str


class DiscoveryRequest(BaseModel):
    case_name: str
    discovery_type: str
    requests_and_responses: list


class SettlementRequest(BaseModel):
    case_name: str
    trigger_point: str
    valuation_data: dict
    recommendation_data: dict


# ---------------------------------------------------------------------------
# Document generation helpers
# ---------------------------------------------------------------------------

DOCUMENT_TRIGGER_WORDS = [
    "draft", "write", "prepare", "create a", "generate a", "compose",
    "produce", "draw up",
]
DOCUMENT_TYPE_WORDS = [
    "letter", "motion", "complaint", "demand", "agreement", "memo",
    "memorandum", "notice", "brief", "contract", "pleading", "declaration",
    "affidavit", "stipulation", "subpoena", "order", "outline", "response",
    "meet and confer", "m&c",
]

DOCUMENT_FORMAT_INSTRUCTIONS = (
    "\n\nIMPORTANT: When drafting any legal document (letter, motion, memo, "
    "demand letter, complaint, agreement, etc.), begin your response with this "
    "exact line:\n"
    "DOCUMENT_TITLE: [short descriptive title, e.g. Meet_and_Confer_Letter_Rodriguez]\n"
    "Then provide the full document text. This allows the system to automatically "
    "create a downloadable Word file for the attorney.\n\n"
)


def is_document_request(message: str) -> bool:
    msg = message.lower()
    has_action = any(kw in msg for kw in DOCUMENT_TRIGGER_WORDS)
    has_doc_type = any(dt in msg for dt in DOCUMENT_TYPE_WORDS)
    return has_action and has_doc_type


def extract_title_and_body(text: str, fallback: str = "Legal_Document") -> tuple[str, str]:
    """Return (title, body) — strips the DOCUMENT_TITLE line if present."""
    lines = text.strip().split("\n")
    if lines and lines[0].strip().startswith("DOCUMENT_TITLE:"):
        title = lines[0].replace("DOCUMENT_TITLE:", "").strip()
        body = "\n".join(lines[1:]).lstrip("\n")
        return title, body
    return fallback, text


def _add_run_with_text(para, text: str):
    """Add a run to a paragraph, applying bold for **...**-wrapped segments."""
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = para.add_run(part[2:-2])
            run.bold = True
        else:
            para.add_run(part)
    for run in para.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def build_docx(title: str, body: str) -> str:
    """Convert title + body text into a formatted .docx file. Returns filename."""
    doc = DocxDocument()

    # Page margins: 1.25" left/right, 1" top/bottom (standard legal)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(title.replace("_", " "))
    title_run.bold = True
    title_run.font.name = "Times New Roman"
    title_run.font.size = Pt(14)
    doc.add_paragraph()  # blank spacer

    # Body — handle markdown-style headings and bold
    for line in body.split("\n"):
        stripped = line.rstrip()

        if not stripped:
            doc.add_paragraph()
            continue

        if stripped.startswith("### "):
            h = doc.add_heading(stripped[4:], level=3)
            for run in h.runs:
                run.font.name = "Times New Roman"
            continue

        if stripped.startswith("## "):
            h = doc.add_heading(stripped[3:], level=2)
            for run in h.runs:
                run.font.name = "Times New Roman"
            continue

        if stripped.startswith("# "):
            h = doc.add_heading(stripped[2:], level=1)
            for run in h.runs:
                run.font.name = "Times New Roman"
            continue

        para = doc.add_paragraph()
        _add_run_with_text(para, stripped)

    safe = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:50]
    filename = f"{safe}_{uuid.uuid4().hex[:6]}.docx"
    doc.save(str(DOCUMENTS_DIR / filename))
    return filename


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>CaseCommand</h1><p>Visit <a href='/docs'>/docs</a> for the API.</p>"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health(_: None = Depends(verify_token)):
    return {"status": "ok", "model": "claude-sonnet-4-6"}


@app.get("/api/cases")
def list_cases(_: None = Depends(verify_token)):
    result = supabase.table("cases").select("*").execute()
    return result.data


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, _: None = Depends(verify_token)):
    result = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Case not found")
    return result.data[0]


@app.post("/api/cases", status_code=201)
def create_case(case: CaseCreate, _: None = Depends(verify_token)):
    data = {
        "case_name": case.name,
        "case_type": case.type,
        "client_name": case.client,
        "opposing_party": case.opposing,
    }
    result = supabase.table("cases").insert(data).execute()
    return result.data[0]


@app.post("/api/chat")
def chat(req: ChatRequest, _: None = Depends(verify_token)):
    cases_result = supabase.table("cases").select("*").eq("status", "active").execute()
    cases = cases_result.data

    if cases:
        cases_context = "\n".join(
            f"- {c.get('case_name', 'Unknown')} "
            f"(Type: {c.get('case_type', '')}, "
            f"Client: {c.get('client_name', '')}, "
            f"Opposing: {c.get('opposing_party', '')})"
            for c in cases
        )
    else:
        cases_context = "No active cases."

    doc_hint = DOCUMENT_FORMAT_INSTRUCTIONS if is_document_request(req.message) else ""

    system_prompt = (
        "You are CaseCommand AI, an expert legal assistant. "
        "You have access to the following active cases:\n\n"
        f"{cases_context}\n\n"
        f"{doc_hint}"
        "Answer the attorney's questions accurately and helpfully."
    )

    response = ai_client._call_api(system_prompt, req.message)
    text = response["text"]

    result = {"reply": text, "model": response["model"], "document": None}

    # Generate .docx when Claude returns a DOCUMENT_TITLE header
    if text.strip().startswith("DOCUMENT_TITLE:"):
        try:
            title, body = extract_title_and_body(text, fallback="Legal_Document")
            filename = build_docx(title, body)
            result["document"] = {
                "filename": filename,
                "url": f"/api/documents/{filename}",
                "title": title.replace("_", " "),
            }
            result["reply"] = body  # show clean body text in chat
        except Exception:
            pass  # never break chat over a docx failure

    return result


@app.get("/api/documents/{filename}", include_in_schema=False)
def download_document(filename: str):
    # Prevent path traversal
    safe_filename = Path(filename).name
    filepath = DOCUMENTS_DIR / safe_filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        str(filepath),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_filename,
    )


@app.get("/api/deadlines")
def deadlines(_: None = Depends(verify_token)):
    result = (
        supabase.table("cases")
        .select("*")
        .eq("status", "active")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


@app.post("/api/discovery")
def analyze_discovery(req: DiscoveryRequest, _: None = Depends(verify_token)):
    response = ai_client.analyze_discovery_responses(
        case_name=req.case_name,
        discovery_type=req.discovery_type,
        requests_and_responses=req.requests_and_responses,
    )
    return {"result": response["text"], "model": response["model"]}


@app.post("/api/settlement")
def generate_settlement(req: SettlementRequest, _: None = Depends(verify_token)):
    response = ai_client.generate_settlement_narrative(
        case_name=req.case_name,
        trigger_point=req.trigger_point,
        valuation_data=req.valuation_data,
        recommendation_data=req.recommendation_data,
    )
    return {"result": response["text"], "model": response["model"]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
