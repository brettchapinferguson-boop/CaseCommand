"""
CaseCommand — AI Feature Routes

Dedicated AI endpoints: discovery analysis, settlement, outlines.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.models.requests import AIRequest, DiscoveryRequest, SettlementRequest, OutlineRequest
from src.auth.jwt import CurrentUser
from src.middleware.rate_limit import limiter

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

OUTLINES_DIR = Path(__file__).parent.parent.parent / "outlines"
OUTLINES_DIR.mkdir(exist_ok=True)


@router.post("/generate")
@limiter.limit("20/minute")
async def ai_generate(req: AIRequest, user: CurrentUser, request: Request):
    """General-purpose AI endpoint for module features."""
    ai_client = request.app.state.ai_client
    try:
        response = ai_client._call_api(req.system, req.message, max_tokens=req.max_tokens)
        return {"text": response["text"], "success": True, "usage": response.get("usage", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discovery")
@limiter.limit("10/minute")
async def analyze_discovery(req: DiscoveryRequest, user: CurrentUser, request: Request):
    """Analyze discovery responses and surface strategic insights."""
    ai_client = request.app.state.ai_client
    response = ai_client.analyze_discovery_responses(
        case_name=req.case_name,
        discovery_type=req.discovery_type,
        requests_and_responses=req.requests_and_responses,
    )
    return {"result": response["text"], "model": response["model"]}


@router.post("/settlement")
@limiter.limit("10/minute")
async def generate_settlement(req: SettlementRequest, user: CurrentUser, request: Request):
    """Generate settlement assessment and negotiation strategy."""
    ai_client = request.app.state.ai_client
    response = ai_client.generate_settlement_narrative(
        case_name=req.case_name,
        trigger_point=req.trigger_point,
        valuation_data=req.valuation_data,
        recommendation_data=req.recommendation_data,
    )
    return {"result": response["text"], "model": response["model"]}


@router.post("/outline")
@limiter.limit("10/minute")
async def generate_outline(req: OutlineRequest, user: CurrentUser, request: Request):
    """Generate examination outline with HTML viewer."""
    ai_client = request.app.state.ai_client
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
    return {"url": f"/api/v1/outlines/{filename}", "model": response["model"]}


@router.get("/outlines/{filename}", include_in_schema=False)
def serve_outline(filename: str, user: CurrentUser):
    """Serve an outline HTML viewer (auth required)."""
    safe = Path(filename).name
    filepath = OUTLINES_DIR / safe
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Outline not found")
    return HTMLResponse(content=filepath.read_text(encoding="utf-8"))


def _build_outline_html(case_name: str, witness_name: str, exam_type: str, outline_text: str) -> str:
    """Parse AI outline text into a self-contained landscape HTML viewer."""
    exam_label = "CROSS-EXAMINATION" if exam_type.lower() == "cross" else "DIRECT EXAMINATION"

    sections: list[dict] = []
    current: dict | None = None
    for raw in outline_text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(#{1,3}|[IVXLC]+\.)\s", line) or (
            re.match(r"^\d+\.", line) and len(line) < 70 and line[0].isdigit() and not line[0:2].isdigit()
        ):
            title = re.sub(r"^#{1,3}\s*|^[IVXLC]+\.\s*", "", line).strip()
            current = {"title": title, "goal": "", "questions": []}
            sections.append(current)
        elif line.lower().startswith("goal:") and current is not None:
            current["goal"] = line[5:].strip()
        elif current is not None and re.match(r"^\d+\.", line):
            q = re.sub(r"^\d+\.\s*", "", line)
            if q:
                current["questions"].append(q)
        elif current is not None and re.match(r"^[-\u2022Q]\s", line):
            q = re.sub(r"^[-\u2022Q][:.]?\s*", "", line)
            if q:
                current["questions"].append(q)

    if not sections:
        questions = [
            re.sub(r"^\d+\.\s*|^[-\u2022]\s*", "", l.strip())
            for l in outline_text.split("\n")
            if l.strip() and re.match(r"^\d+\.|^[-\u2022]", l.strip())
        ]
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

    # Keep the HTML template compact — same layout as before
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{exam_label} -- {witness_name}</title>
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
}}
</style>
</head>
<body>
<div class="hdr">
  <div>
    <div class="hdr-title">{exam_label}: {witness_name}</div>
    <div class="hdr-sub">{case_name} -- CaseCommand</div>
  </div>
  <div class="hdr-btns">
    <button onclick="prev()">Prev</button>
    <span id="counter" style="color:#aaa;font-size:12px;align-self:center">0 / {q_num - 1}</span>
    <button onclick="next()">Next</button>
    <button onclick="window.print()">Print</button>
  </div>
</div>
<div class="workspace">
  <div class="q-panel">
    <div class="q-panel-hdr">Examination Questions</div>
    <div class="q-scroll" id="qScroll">{sections_html}</div>
    <div class="kb-hint">Arrow keys to navigate - Click question to select</div>
  </div>
  <div class="ex-panel">
    <div class="ex-panel-hdr">Current Question / Exhibit Reference</div>
    <div class="ex-content">
      <div class="q-display" id="qDisplay"></div>
      <div class="exhibit-ph" id="exPh">
        <h3>Select a question to begin</h3>
        <p>Click any question on the left or use arrow keys.</p>
      </div>
    </div>
  </div>
</div>
<script>
const items=Array.from(document.querySelectorAll('.q-item'));
const total=items.length;
let idx=-1;
function selectQ(el){{items.forEach(i=>i.classList.remove('active'));el.classList.add('active');idx=items.indexOf(el);document.getElementById('qDisplay').textContent=el.textContent;document.getElementById('qDisplay').classList.add('show');document.getElementById('exPh').style.display='none';document.getElementById('counter').textContent=(idx+1)+' / '+total;el.scrollIntoView({{block:'nearest'}});}}
function next(){{if(idx<total-1)selectQ(items[idx+1]);}}
function prev(){{if(idx>0)selectQ(items[idx-1]);}}
document.addEventListener('keydown',e=>{{if(e.key==='ArrowDown'){{e.preventDefault();next();}}if(e.key==='ArrowUp'){{e.preventDefault();prev();}}}});
if(total>0)selectQ(items[0]);
</script>
</body>
</html>"""
