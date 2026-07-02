"""
CaseCommand — Agent Tools
==========================
Tool definitions and executors for the CaseCommander/paralegal agents.

Design constraints (professional responsibility by architecture):
- NO tool can send email, file with a court, or contact any external party.
  All work product lands in the database with status 'pending_review' and
  must be approved by the supervising attorney (RPC 5.3; ABA Op. 512).
- Every tool execution is written to the audit log.
- Drafted documents containing citations auto-generate a
  "verify citations" task — computed citations are never trusted blind.
"""

import json
import re
import uuid
import logging
from datetime import date
from typing import Dict, List

import database as db
import rules

logger = logging.getLogger("casecommand.tools")

# Document types the agents may draft
DOC_TYPES = [
    "mc_letter", "motion", "separate_statement", "declaration",
    "proposed_order", "complaint", "discovery_requests", "demand_letter",
    "cross_outline", "memo", "digest", "other",
]

CITATION_PATTERN = re.compile(r"(\sv\.\s|§|CCP|Cal\.|CRC\s|F\.\d|Cal\.App\.)")


# ── Tool schemas (Anthropic tool-use format) ──────
TOOL_DEFINITIONS: List[Dict] = [
    {
        "name": "list_cases",
        "description": "List all cases in the practice with their key data.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_case",
        "description": "Get full detail for one case by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {"case_id": {"type": "string"}},
            "required": ["case_id"],
        },
    },
    {
        "name": "update_case",
        "description": ("Update fields on a case (phase, specials, valuation, "
                        "modules, number, etc.). Only pass fields to change."),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "description": ("Fields to update: name, number, type, client, "
                                    "opposing, phase (0-8), specials, valuation "
                                    "{lo,mid,hi}, deadline, modules"),
                },
            },
            "required": ["case_id", "updates"],
        },
    },
    {
        "name": "compute_deadlines",
        "description": (
            "Compute California litigation deadlines from a trigger event using "
            "CCP/CRC rules with court-day and service-extension math. Returns "
            "computed dates WITHOUT saving them — review, then use add_deadline "
            f"to calendar the ones that apply. Trigger events: {', '.join(rules.TRIGGER_EVENTS)}"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_event": {"type": "string", "enum": rules.TRIGGER_EVENTS},
                "event_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "service_method": {
                    "type": "string",
                    "enum": list(rules.SERVICE_EXTENSIONS.keys()),
                    "description": "How the triggering document was served (affects extensions)",
                },
            },
            "required": ["trigger_event", "event_date"],
        },
    },
    {
        "name": "add_deadline",
        "description": "Calendar a deadline for a case with its governing rule citation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "title": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "rule": {"type": "string", "description": "Statute/rule citation"},
                "note": {"type": "string"},
            },
            "required": ["case_id", "title", "due_date"],
        },
    },
    {
        "name": "list_deadlines",
        "description": "List pending deadlines, optionally limited to the next N days or one case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "within_days": {"type": "integer"},
                "case_id": {"type": "string"},
            },
        },
    },
    {
        "name": "update_deadline_status",
        "description": "Mark a deadline satisfied (work completed) or missed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deadline_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "satisfied", "missed"]},
            },
            "required": ["deadline_id", "status"],
        },
    },
    {
        "name": "create_task",
        "description": ("Create a work item / action item. Use for anything that "
                        "needs doing: drafting, verification, follow-ups, attorney "
                        "decisions needed."),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "detail": {"type": "string"},
                "case_id": {"type": "string"},
                "priority": {"type": "string", "enum": ["urgent", "high", "medium", "low"]},
                "due_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks, optionally filtered by status (open/in_progress/done/dismissed) or case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "case_id": {"type": "string"},
            },
        },
    },
    {
        "name": "update_task",
        "description": "Change a task's status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "status": {"type": "string", "enum": ["open", "in_progress", "done", "dismissed"]},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "save_document",
        "description": (
            "Save drafted work product (letter, motion, memo, etc.). The document "
            "enters the attorney review queue as 'pending_review' — it is NOT sent "
            "or filed. Draft complete, ready-to-review documents, not outlines."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "doc_type": {"type": "string", "enum": DOC_TYPES},
                "title": {"type": "string"},
                "content": {"type": "string", "description": "Full document text"},
            },
            "required": ["doc_type", "title", "content"],
        },
    },
    {
        "name": "list_documents",
        "description": "List documents, optionally filtered by status (pending_review/approved/rejected/draft) or case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "case_id": {"type": "string"},
            },
        },
    },
    {
        "name": "log_note",
        "description": "Record an observation or decision rationale in the case audit trail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string"},
                "case_id": {"type": "string"},
            },
            "required": ["note"],
        },
    },
]


# ── Tool executor ─────────────────────────────────
async def execute_tool(name: str, tool_input: Dict, actor: str = "agent") -> str:
    """Execute one tool call and return a JSON string result.
    Errors are returned as strings so the agent can self-correct."""
    try:
        result = await _dispatch(name, tool_input, actor)
        return json.dumps(result, default=str)
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return json.dumps({"error": f"{type(e).__name__}: {e}"})


async def _dispatch(name: str, i: Dict, actor: str):
    if name == "list_cases":
        return {"cases": await db.get_all_cases()}

    if name == "get_case":
        case = await db.get_case(i["case_id"])
        return case or {"error": "Case not found"}

    if name == "update_case":
        updated = await db.update_case(i["case_id"], i.get("updates", {}))
        if not updated:
            return {"error": "Case not found"}
        await db.log_audit(actor, "update_case", "case", i["case_id"],
                           json.dumps(i.get("updates", {}), default=str))
        return updated

    if name == "compute_deadlines":
        event_date = date.fromisoformat(i["event_date"])
        computed = rules.compute_deadlines(
            i["trigger_event"], event_date, i.get("service_method", "personal")
        )
        await db.log_audit(actor, "compute_deadlines", "rules",
                           i["trigger_event"], json.dumps(computed))
        return {"deadlines": computed,
                "warning": "Computed dates require attorney verification against local rules"}

    if name == "add_deadline":
        date.fromisoformat(i["due_date"])  # validate format
        dl = await db.create_deadline({
            "id": str(uuid.uuid4())[:8],
            "case_id": i["case_id"],
            "title": i["title"],
            "rule": i.get("rule", ""),
            "due_date": i["due_date"],
            "note": i.get("note", ""),
            "created_by": actor,
        })
        await db.log_audit(actor, "add_deadline", "deadline", dl["id"],
                           f"{i['title']} due {i['due_date']}")
        return dl

    if name == "list_deadlines":
        return {"deadlines": await db.list_deadlines(
            within_days=i.get("within_days"), case_id=i.get("case_id"))}

    if name == "update_deadline_status":
        dl = await db.update_deadline_status(i["deadline_id"], i["status"])
        if not dl:
            return {"error": "Deadline not found"}
        await db.log_audit(actor, "update_deadline_status", "deadline",
                           i["deadline_id"], i["status"])
        return dl

    if name == "create_task":
        task = await db.create_task({
            "id": str(uuid.uuid4())[:8],
            "case_id": i.get("case_id"),
            "title": i["title"],
            "detail": i.get("detail", ""),
            "priority": i.get("priority", "medium"),
            "due_date": i.get("due_date"),
            "created_by": actor,
        })
        await db.log_audit(actor, "create_task", "task", task["id"], i["title"])
        return task

    if name == "list_tasks":
        return {"tasks": await db.list_tasks(
            status=i.get("status"), case_id=i.get("case_id"))}

    if name == "update_task":
        task = await db.update_task_status(i["task_id"], i["status"])
        if not task:
            return {"error": "Task not found"}
        await db.log_audit(actor, "update_task", "task", i["task_id"], i["status"])
        return task

    if name == "save_document":
        doc = await db.create_document({
            "id": str(uuid.uuid4())[:8],
            "case_id": i.get("case_id"),
            "doc_type": i["doc_type"],
            "title": i["title"],
            "content": i["content"],
            "status": "pending_review",
            "created_by": actor,
        })
        await db.log_audit(actor, "save_document", "document", doc["id"],
                           f"{i['doc_type']}: {i['title']}")
        # Guardrail: any draft containing legal citations gets a mandatory
        # verification task — AI citations are never trusted unverified.
        if i["doc_type"] != "digest" and CITATION_PATTERN.search(i["content"]):
            vt = await db.create_task({
                "id": str(uuid.uuid4())[:8],
                "case_id": i.get("case_id"),
                "title": f"Verify all citations in: {i['title']}",
                "detail": ("AI-drafted document contains legal citations. Attorney "
                           "must independently verify each authority exists and "
                           "supports the proposition before approval (ABA Op. 512; "
                           "Noland v. Land of the Free (Cal. Ct. App. 2025) — $10K "
                           "sanctions for unverified AI citations; proposed CA RPC "
                           "1.1 verification amendment)."),
                "priority": "high",
                "created_by": "system",
            })
            await db.log_audit("system", "create_task", "task", vt["id"],
                               "Auto citation-verification task")
        return {"document_id": doc["id"], "status": doc["status"],
                "note": "Saved to attorney review queue. Not sent or filed."}

    if name == "list_documents":
        docs = await db.list_documents(status=i.get("status"), case_id=i.get("case_id"))
        # Trim content in listings to keep tool results small
        return {"documents": [
            {**d, "content": (d["content"][:300] + "…") if len(d["content"]) > 300 else d["content"]}
            for d in docs
        ]}

    if name == "log_note":
        await db.log_audit(actor, "note", "case", i.get("case_id", ""), i["note"])
        return {"logged": True}

    return {"error": f"Unknown tool: {name}"}
