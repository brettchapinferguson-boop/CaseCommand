"""
CaseCommand — Unified Agent Engine

Single agent loop that processes messages from any channel (web, Telegram,
WhatsApp/SMS) and routes through the same Casey persona + tool set.

Multi-tenant: uses firm_config from context to personalize the system prompt
for each organization.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from src.config import get_settings


def _load_soul() -> str:
    """Load SOUL.md from project root as the base system prompt."""
    settings = get_settings()
    if settings.SOUL_PATH.exists():
        return settings.SOUL_PATH.read_text(encoding="utf-8")
    return (
        "You are Casey, the lead litigation assistant for CaseCommand. "
        "You act as an expert trial attorney and elite paralegal."
    )


SOUL = _load_soul()

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
        "name": "search_case_documents",
        "description": (
            "Search through uploaded case documents (depositions, exhibits, "
            "pleadings, contracts, etc.) using semantic search. Use this when "
            "the user asks about specific facts, quotes, or details from their "
            "case files. Returns relevant excerpts with source information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — what to look for in the documents.",
                },
                "case_id": {
                    "type": "string",
                    "description": "Optional case ID to scope the search to a specific case.",
                },
            },
            "required": ["query"],
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
# Multi-tenant system prompt builder
# ---------------------------------------------------------------------------


def _build_system_prompt(firm_config: dict | None = None) -> str:
    """
    Build a tenant-specific system prompt.

    If firm_config is provided, overrides the default SOUL.md firm details.
    This allows each law firm to have their own identity in Casey's responses.
    """
    if not firm_config:
        return SOUL

    firm_name = firm_config.get("firm_name", "")
    attorney_name = firm_config.get("attorney_name", "")
    bar_number = firm_config.get("bar_number", "")
    jurisdiction = firm_config.get("jurisdiction", "California")
    firm_address = firm_config.get("firm_address", "")
    court_formatting = firm_config.get("court_formatting", "")

    firm_section = ""
    if firm_name or attorney_name:
        firm_section = f"""

## Firm Identity (This Session)
- Firm: {firm_name}
- Attorney: {attorney_name}{'  (SBN ' + bar_number + ')' if bar_number else ''}
- Jurisdiction: {jurisdiction}
{f'- Address: {firm_address}' if firm_address else ''}
{f'- Court Formatting: {court_formatting}' if court_formatting else ''}

When drafting documents, use this firm's identity in headers and signature blocks.
"""

    base = SOUL
    if "Brett Ferguson" in base and firm_name:
        base = base.replace(
            "Brett Ferguson\n(SBN 281519), Law Office of Brett Ferguson, Long Beach, California",
            f"{attorney_name}, {firm_name}",
        )
        base = base.replace(
            "Brett Ferguson (SBN 281519), Law Office of Brett Ferguson,\n  Long Beach, CA",
            f"{attorney_name}{' (SBN ' + bar_number + ')' if bar_number else ''}, {firm_name}",
        )

    doc_intelligence = """

## Document Intelligence
You have access to documents uploaded to cases. When users ask about specific
facts, testimony, contract terms, or evidence, use the search_case_documents
tool to find relevant excerpts. Always cite the source document and page number.
"""

    return base + firm_section + doc_intelligence


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get_headers() -> dict:
    settings = get_settings()
    return {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


async def _call_claude(
    messages: list,
    tools: list | None = None,
    max_tokens: int = 4096,
    system_prompt: str | None = None,
) -> dict:
    """Single async call to the Anthropic Messages API."""
    settings = get_settings()
    payload: dict = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt or SOUL,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(
        timeout=120.0, trust_env=False, proxy=settings.get_proxy()
    ) as client:
        resp = await client.post(
            f"{settings.ANTHROPIC_BASE_URL}/messages",
            headers=_get_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Tool execution — called when Claude invokes a tool
# ---------------------------------------------------------------------------


async def _execute_tool(name: str, input_data: dict, context: dict) -> dict:
    """Execute a tool and return its result."""
    supabase = context.get("supabase")
    org_id = context.get("org_id")

    if name == "generate_legal_document":
        return {
            "status": "success",
            "message": f"Document '{input_data['title']}' generated successfully.",
        }

    if name == "lookup_case":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        query_text = input_data.get("query", "").lower()
        q = supabase.table("cases").select("*").eq("status", "active")
        if org_id:
            q = q.eq("org_id", org_id)
        result = q.execute()
        matches = [
            c for c in (result.data or [])
            if query_text in (c.get("case_name") or "").lower()
            or query_text in (c.get("client_name") or "").lower()
            or query_text in (c.get("case_type") or "").lower()
        ]
        if matches:
            return {"status": "success", "cases": matches}
        return {"status": "success", "cases": [], "message": "No matching cases found."}

    if name == "list_deadlines":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        q = supabase.table("cases").select("*").eq("status", "active").order("created_at", desc=False)
        if org_id:
            q = q.eq("org_id", org_id)
        result = q.execute()
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
        if org_id:
            data["org_id"] = org_id
        if context.get("user_id"):
            data["user_id"] = context["user_id"]
        result = supabase.table("cases").insert(data).execute()
        return {"status": "success", "case": result.data[0] if result.data else data}

    if name == "search_case_documents":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.rag.query import RAGQueryEngine

            engine = RAGQueryEngine(supabase_client=supabase)
            results = await engine.search(
                query=input_data["query"],
                org_id=org_id,
                case_id=input_data.get("case_id"),
            )
            if not results:
                return {
                    "status": "success",
                    "results": [],
                    "message": "No matching documents found.",
                }
            formatted = []
            for r in results:
                formatted.append(
                    f"[Source: {r['source']} | Chunk {r['chunk_index']} | "
                    f"Score: {r['similarity']}]\n{r['content']}"
                )
            return {
                "status": "success",
                "results": formatted,
                "count": len(formatted),
            }
        except Exception as e:
            return {"status": "error", "message": f"Document search failed: {e}"}

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
        context: Dict with 'supabase' client, 'org_id', 'firm_config', etc.

    Returns:
        {
            "reply": str,
            "tool_calls": list,
            "model": str,
            "usage": dict,
        }
    """
    ctx = context or {}
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    # Build tenant-specific system prompt
    firm_config = ctx.get("firm_config")
    system_prompt = _build_system_prompt(firm_config)

    # Inject active cases context
    supabase = ctx.get("supabase")
    org_id = ctx.get("org_id")
    if supabase:
        try:
            q = supabase.table("cases").select("*").eq("status", "active")
            if org_id:
                q = q.eq("org_id", org_id)
            cases_result = q.execute()
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
    reply_text = ""
    data = {}

    for _ in range(max_iterations):
        data = await _call_claude(messages, tools=TOOLS, system_prompt=system_prompt)
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
            return {
                "reply": reply_text.strip(),
                "tool_calls": all_tool_calls,
                "model": data.get("model", get_settings().CLAUDE_MODEL),
                "usage": data.get("usage", {}),
            }

        messages.append({"role": "assistant", "content": content_blocks})

        tool_results = []
        for tu in tool_uses:
            tool_call_record = {
                "id": tu["id"],
                "name": tu["name"],
                "input": tu["input"],
            }
            all_tool_calls.append(tool_call_record)

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

    return {
        "reply": reply_text.strip() if reply_text else "I encountered a complex request. Could you try rephrasing?",
        "tool_calls": all_tool_calls,
        "model": data.get("model", get_settings().CLAUDE_MODEL),
        "usage": data.get("usage", {}),
    }
