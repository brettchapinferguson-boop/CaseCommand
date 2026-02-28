"""
CaseCommand — Unified Agent Engine

Single agent loop that processes messages from any channel (web, Telegram,
WhatsApp/SMS) and routes through the same Casey persona + tool set.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx


def _load_soul() -> str:
    """Load SOUL.md from project root as the base system prompt."""
    soul_path = Path(__file__).parent.parent / "SOUL.md"
    if soul_path.exists():
        return soul_path.read_text(encoding="utf-8")
    return (
        "You are Casey, the lead litigation assistant for CaseCommand. "
        "You act as an expert trial attorney and elite paralegal."
    )


SOUL = _load_soul()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
BASE_URL = "https://api.anthropic.com/v1"

# ---------------------------------------------------------------------------
# Tool definitions — everything Casey can do
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "generate_legal_document",
        "description": (
            "Draft a substantive legal document (e.g., Meet and Confer letter, "
            "motion, pleading, settlement agreement, demand letter). Use this "
            "whenever the user asks to draft, write, or generate a document. "
            "Returns structured JSON with title and body so the system can "
            "compile a downloadable .docx file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short descriptive filename, e.g., Meet_and_Confer_Smith_v_Jones",
                },
                "body": {
                    "type": "string",
                    "description": (
                        "The fully formatted text of the legal document. "
                        "Use markdown for headers (###) and bolding (**text**)."
                    ),
                },
            },
            "required": ["title", "body"],
        },
    },
    {
        "name": "lookup_case",
        "description": (
            "Search active cases in the database by name, client, or type. "
            "Use this when the user references a case or asks about case status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term: case name, client name, or case type.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_deadlines",
        "description": (
            "List upcoming deadlines across all active cases. "
            "Use when the user asks about deadlines, calendar, or what's coming up."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_case",
        "description": (
            "Create a new case in the database. Use when the user wants to "
            "open or create a new case file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_name": {
                    "type": "string",
                    "description": "Full case name, e.g., Rodriguez v. Smith Trucking",
                },
                "case_type": {
                    "type": "string",
                    "description": "Case type: PI, Employment, Contract, Criminal, Family, Real Estate, Other",
                },
                "client_name": {
                    "type": "string",
                    "description": "Client's full name",
                },
                "opposing_party": {
                    "type": "string",
                    "description": "Opposing party name",
                },
            },
            "required": ["case_name", "case_type", "client_name", "opposing_party"],
        },
    },
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get_headers() -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _get_proxy() -> str | None:
    p = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
    )
    return p if p and not p.startswith("socks") else None


async def _call_claude(messages: list, tools: list | None = None, max_tokens: int = 4096) -> dict:
    """Single async call to the Anthropic Messages API."""
    payload: dict = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": SOUL,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(
        timeout=120.0, trust_env=False, proxy=_get_proxy()
    ) as client:
        resp = await client.post(
            f"{BASE_URL}/messages",
            headers=_get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Tool execution — called when Claude invokes a tool
# ---------------------------------------------------------------------------


async def _execute_tool(name: str, input_data: dict, context: dict) -> dict:
    """
    Execute a tool and return its result.

    `context` carries objects the tools may need (supabase client, etc.).
    """
    supabase = context.get("supabase")

    if name == "generate_legal_document":
        # The actual docx build happens in server.py after we return the tool call.
        # Here we just confirm the tool was invoked so the agent loop returns it.
        return {
            "status": "success",
            "message": f"Document '{input_data['title']}' generated successfully.",
        }

    if name == "lookup_case":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        query = input_data.get("query", "").lower()
        result = supabase.table("cases").select("*").eq("status", "active").execute()
        matches = [
            c for c in (result.data or [])
            if query in (c.get("case_name") or "").lower()
            or query in (c.get("client_name") or "").lower()
            or query in (c.get("case_type") or "").lower()
        ]
        if matches:
            return {"status": "success", "cases": matches}
        return {"status": "success", "cases": [], "message": "No matching cases found."}

    if name == "list_deadlines":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        result = (
            supabase.table("cases")
            .select("*")
            .eq("status", "active")
            .order("created_at", desc=False)
            .execute()
        )
        return {"status": "success", "cases": result.data or []}

    if name == "create_case":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        data = {
            "case_name": input_data["case_name"],
            "case_type": input_data["case_type"],
            "client_name": input_data["client_name"],
            "opposing_party": input_data["opposing_party"],
        }
        result = supabase.table("cases").insert(data).execute()
        return {"status": "success", "case": result.data[0] if result.data else data}

    return {"status": "error", "message": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agent loop — the core message processor
# ---------------------------------------------------------------------------


async def process_message(
    user_message: str,
    *,
    conversation_history: list | None = None,
    context: dict | None = None,
) -> dict:
    """
    Process a single user message through the Casey agent.

    Args:
        user_message: The text from the user.
        conversation_history: Optional prior messages for multi-turn context.
        context: Dict with 'supabase' client and any other dependencies.

    Returns:
        {
            "reply": str,           # Text reply for the user
            "tool_calls": list,     # Any tool invocations (for server-side handling)
            "model": str,
        }
    """
    ctx = context or {}
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    # Inject active cases context into the conversation
    supabase = ctx.get("supabase")
    if supabase:
        try:
            cases_result = supabase.table("cases").select("*").eq("status", "active").execute()
            cases = cases_result.data or []
            if cases:
                cases_ctx = "\n".join(
                    f"- {c.get('case_name', 'Unknown')} "
                    f"(Type: {c.get('case_type', '')}, "
                    f"Client: {c.get('client_name', '')}, "
                    f"Opposing: {c.get('opposing_party', '')})"
                    for c in cases
                )
            else:
                cases_ctx = "No active cases."
        except Exception:
            cases_ctx = "Database unavailable."
    else:
        cases_ctx = "Database not connected."

    # Prepend cases context as a system-injected user message if this is the
    # first message in the conversation
    if len(messages) == 1:
        messages.insert(0, {
            "role": "user",
            "content": f"[System: Active cases]\n{cases_ctx}",
        })
        messages.insert(1, {
            "role": "assistant",
            "content": "Understood. I have the current case roster. How can I help?",
        })

    # --- Agent loop: call Claude, handle tool use, repeat ---
    max_iterations = 5
    all_tool_calls: list[dict] = []

    for _ in range(max_iterations):
        data = await _call_claude(messages, tools=TOOLS)
        content_blocks = data.get("content", [])
        stop_reason = data.get("stop_reason", "end_turn")

        reply_text = ""
        tool_uses = []

        for block in content_blocks:
            if block["type"] == "text":
                reply_text += block["text"]
            elif block["type"] == "tool_use":
                tool_uses.append(block)

        if not tool_uses or stop_reason != "tool_use":
            # No tools invoked — return the text reply
            return {
                "reply": reply_text.strip(),
                "tool_calls": all_tool_calls,
                "model": data.get("model", MODEL),
            }

        # Claude wants to use tools — execute them and loop
        # First, add Claude's response (with tool_use blocks) to messages
        messages.append({"role": "assistant", "content": content_blocks})

        # Execute each tool and build the tool_result message
        tool_results = []
        for tu in tool_uses:
            tool_call_record = {
                "id": tu["id"],
                "name": tu["name"],
                "input": tu["input"],
            }
            all_tool_calls.append(tool_call_record)

            # generate_legal_document is handled post-loop by the server
            if tu["name"] == "generate_legal_document":
                result = {
                    "status": "success",
                    "message": f"Document '{tu['input'].get('title', 'document')}' will be compiled.",
                }
            else:
                result = await _execute_tool(tu["name"], tu["input"], ctx)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    # Fallback if we exhaust iterations
    return {
        "reply": reply_text.strip() if reply_text else "I encountered a complex request. Could you try rephrasing?",
        "tool_calls": all_tool_calls,
        "model": data.get("model", MODEL),
    }
