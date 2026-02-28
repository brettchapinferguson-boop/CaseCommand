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
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
ai_client = CaseCommandAI()

# ---------------------------------------------------------------------------
# Document storage
# ---------------------------------------------------------------------------

DOCUMENTS_DIR = Path(__file__).parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

OUTLINES_DIR = Path(__file__).parent / "outlines"
OUTLINES_DIR.mkdir(exist_ok=True)

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


class OutlineRequest(BaseModel):
    case_name: str
    witness_name: str
    witness_role: str = "witness"
    exam_type: str = "cross"
    case_theory: str = ""
    documents: list = []


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


def _title_from_message(message: str) -> str:
    """Derive a safe document filename from the user's request."""
    skip = {"a", "an", "the", "for", "of", "in", "to", "me", "us", "please", "can", "you"}
    words = [w.capitalize() for w in message.split() if w.lower() not in skip]
    return "_".join(words[:6]) or "Legal_Document"


def extract_title_and_body(text: str, fallback: str = "Legal_Document") -> tuple[str, str]:
    """Return (title, body) — strips the DOCUMENT_TITLE line wherever it appears."""
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("DOCUMENT_TITLE:"):
            title = line.replace("DOCUMENT_TITLE:", "").strip()
            body = "\n".join(lines[:i] + lines[i + 1:]).lstrip("\n")
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
async def chat(req: ChatRequest, _: None = Depends(verify_token)):
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

    # Use the async agent loop — Claude decides whether to reply or use a tool
    response = await ai_client.chat_agent_loop(req.message, cases_context)

    result = {"reply": response["reply"].strip(), "model": response["model"], "document": None}

    # If Claude used the generate_legal_document tool, build the .docx
    for tool_call in response.get("tool_calls", []):
        if tool_call["name"] == "generate_legal_document":
            try:
                title = tool_call["input"]["title"]
                body = tool_call["input"]["body"]
                filename = build_docx(title, body)
                result["document"] = {
                    "filename": filename,
                    "url": f"/api/documents/{filename}",
                    "title": title.replace("_", " "),
                }
                # Show clean body text in chat if reply was empty (tool-only response)
                if not result["reply"]:
                    result["reply"] = body
            except Exception:
                pass  # never break chat over a docx failure

    # Fallback: still handle the old DOCUMENT_TITLE: marker for backwards compat
    if not result["document"] and "DOCUMENT_TITLE:" in result["reply"]:
        try:
            fallback = _title_from_message(req.message)
            title, body = extract_title_and_body(result["reply"], fallback=fallback)
            filename = build_docx(title, body)
            result["document"] = {
                "filename": filename,
                "url": f"/api/documents/{filename}",
                "title": title.replace("_", " "),
            }
            result["reply"] = body
        except Exception:
            pass

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
# TrialOutline Pro — landscape HTML viewer
# ---------------------------------------------------------------------------


def build_outline_html(case_name: str, witness_name: str, exam_type: str, outline_text: str) -> str:
    """Parse AI outline text into a self-contained landscape HTML viewer."""
    exam_label = "CROSS-EXAMINATION" if exam_type.lower() == "cross" else "DIRECT EXAMINATION"

    # Parse sections and questions
    sections: list[dict] = []
    current: dict | None = None
    for raw in outline_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(#{1,3}|[IVXLC]+\.)\s", line) or (re.match(r"^\d+\.", line) and len(line) < 70 and line[0].isdigit() and not line[0:2].isdigit()):
            title = re.sub(r"^#{1,3}\s*|^[IVXLC]+\.\s*", "", line).strip()
            current = {"title": title, "goal": "", "questions": []}
            sections.append(current)
        elif line.lower().startswith("goal:") and current is not None:
            current["goal"] = line[5:].strip()
        elif current is not None and re.match(r"^\d+\.", line):
            q = re.sub(r"^\d+\.\s*", "", line)
            if q:
                current["questions"].append(q)
        elif current is not None and re.match(r"^[-•Q]\s", line):
            q = re.sub(r"^[-•Q][:.]?\s*", "", line)
            if q:
                current["questions"].append(q)

    if not sections:
        questions = [re.sub(r"^\d+\.\s*|^[-•]\s*", "", l.strip())
                     for l in outline_text.split("\n")
                     if l.strip() and re.match(r"^\d+\.|^[-•]", l.strip())]
        sections = [{"title": "Examination Questions", "goal": "", "questions": questions or ["(No questions parsed)"]}]

    q_num = 1
    sections_html = ""
    for sec in sections:
        items_html = ""
        for q in sec["questions"]:
            items_html += f'<div class="q-item" data-q="{q_num}" onclick="selectQ(this)">{q_num}. {q}</div>\n'
            q_num += 1
        goal_html = f'<div class="sec-goal">Goal: {sec["goal"]}</div>' if sec["goal"] else ""
        sections_html += f"""<div class="section">
  <div class="sec-title">{sec["title"].upper()}</div>{goal_html}{items_html}</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{exam_label} — {witness_name}</title>
<style>
@page {{ size: landscape; margin: 0.5in; }}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:"Times New Roman",serif; background:#f0f2f5; height:100vh; display:flex; flex-direction:column; overflow:hidden; }}
.hdr {{ background:#1a1a2e; color:#fff; padding:10px 20px; display:flex; align-items:center; justify-content:space-between; flex-shrink:0; }}
.hdr-title {{ font-size:15px; font-weight:700; }}
.hdr-sub {{ font-size:11px; color:#aaa; margin-top:2px; }}
.hdr-btns {{ display:flex; gap:8px; }}
.hdr-btns button {{ padding:4px 12px; border-radius:4px; border:1px solid #555; background:transparent; color:#ccc; cursor:pointer; font-size:12px; }}
.hdr-btns button:hover {{ background:#2a2a4e; color:#fff; }}
.workspace {{ display:flex; flex:1; overflow:hidden; }}
.q-panel {{ width:42%; background:#fff; border-right:2px solid #dee2e6; display:flex; flex-direction:column; overflow:hidden; }}
.q-panel-hdr {{ background:#2c3e50; color:#fff; padding:8px 14px; font-size:12px; font-weight:700; letter-spacing:.3px; flex-shrink:0; }}
.q-scroll {{ flex:1; overflow-y:auto; padding:10px; }}
.section {{ margin-bottom:14px; }}
.sec-title {{ font-size:10px; font-weight:700; color:#495057; background:#e9ecef; padding:3px 8px; border-radius:3px; margin-bottom:3px; letter-spacing:.5px; }}
.sec-goal {{ font-size:10px; color:#6c757d; font-style:italic; padding:2px 8px 3px; }}
.q-item {{ padding:6px 10px; border-radius:4px; margin-bottom:2px; font-size:12px; cursor:pointer; border-left:3px solid transparent; line-height:1.4; transition:background .1s; }}
.q-item:hover {{ background:#f0f4ff; border-left-color:#4a90e2; }}
.q-item.active {{ background:#dbeafe; border-left-color:#1d4ed8; font-weight:600; }}
.kb-hint {{ font-size:10px; color:#6c757d; text-align:center; padding:5px; border-top:1px solid #dee2e6; background:#f8f9fa; flex-shrink:0; }}
.ex-panel {{ width:58%; background:#fff; display:flex; flex-direction:column; overflow:hidden; }}
.ex-panel-hdr {{ background:#155724; color:#fff; padding:8px 14px; font-size:12px; font-weight:700; flex-shrink:0; }}
.ex-content {{ flex:1; overflow-y:auto; padding:20px; }}
.q-display {{ background:#1d4ed8; color:#fff; padding:14px 18px; border-radius:8px; margin-bottom:20px; font-size:14px; font-weight:500; line-height:1.5; display:none; }}
.q-display.show {{ display:block; }}
.exhibit-ph {{ border:2px dashed #dee2e6; border-radius:8px; padding:40px 30px; text-align:center; color:#adb5bd; }}
.exhibit-ph h3 {{ font-size:15px; margin-bottom:8px; color:#6c757d; }}
.exhibit-ph p {{ font-size:12px; line-height:1.6; }}
@media print {{
  body {{ height:auto; overflow:visible; }}
  .hdr-btns {{ display:none; }}
  .workspace {{ page-break-inside:avoid; }}
}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <div class="hdr-title">⚖️ {exam_label}: {witness_name}</div>
    <div class="hdr-sub">{case_name} &nbsp;·&nbsp; CaseCommand by LawClaw</div>
  </div>
  <div class="hdr-btns">
    <button onclick="prev()">← Prev</button>
    <span id="counter" style="color:#aaa;font-size:12px;align-self:center">0 / {q_num - 1}</span>
    <button onclick="next()">Next →</button>
    <button onclick="window.print()">🖨 Print</button>
    <button onclick="window.close()">✕ Close</button>
  </div>
</div>
<div class="workspace">
  <div class="q-panel">
    <div class="q-panel-hdr">📋 Examination Questions</div>
    <div class="q-scroll" id="qScroll">{sections_html}</div>
    <div class="kb-hint">↑ ↓ Arrow keys to navigate · Click question to select</div>
  </div>
  <div class="ex-panel">
    <div class="ex-panel-hdr">📄 Current Question / Exhibit Reference</div>
    <div class="ex-content">
      <div class="q-display" id="qDisplay"></div>
      <div class="exhibit-ph" id="exPh">
        <h3>Select a question to begin</h3>
        <p>Click any question on the left or use ↑↓ arrow keys.<br>
        The question will appear here in large text for easy reference at counsel table.<br><br>
        Exhibits can be added to CaseCommand cases to display alongside questions.</p>
      </div>
    </div>
  </div>
</div>
<script>
const items = Array.from(document.querySelectorAll('.q-item'));
const total = items.length;
let idx = -1;
function selectQ(el) {{
  items.forEach(i => i.classList.remove('active'));
  el.classList.add('active');
  idx = items.indexOf(el);
  document.getElementById('qDisplay').textContent = el.textContent;
  document.getElementById('qDisplay').classList.add('show');
  document.getElementById('exPh').style.display = 'none';
  document.getElementById('counter').textContent = (idx+1) + ' / ' + total;
  el.scrollIntoView({{block:'nearest'}});
}}
function next() {{ if (idx < total-1) selectQ(items[idx+1]); }}
function prev() {{ if (idx > 0) selectQ(items[idx-1]); }}
document.addEventListener('keydown', e => {{
  if (e.key==='ArrowDown') {{ e.preventDefault(); next(); }}
  if (e.key==='ArrowUp')   {{ e.preventDefault(); prev(); }}
}});
if (total > 0) selectQ(items[0]);
</script>
</body>
</html>"""


@app.post("/api/outline")
def generate_outline(req: OutlineRequest, _: None = Depends(verify_token)):
    response = ai_client.generate_examination_outline(
        case_name=req.case_name,
        witness_name=req.witness_name,
        witness_role=req.witness_role,
        exam_type=req.exam_type,
        case_documents=req.documents,
        case_theory=req.case_theory,
    )
    html = build_outline_html(
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
def serve_outline(filename: str):
    safe = Path(filename).name
    filepath = OUTLINES_DIR / safe
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Outline not found")
    return HTMLResponse(content=filepath.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
