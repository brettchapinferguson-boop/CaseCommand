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
    # --- Intake ---
    {
        "name": "analyze_intake",
        "description": (
            "Analyze a potential client intake for case viability. Identifies causes of action, "
            "maps facts to prima facie elements, checks statute of limitations, flags affirmative "
            "defenses, and generates a viability scorecard. Use when the user describes a potential "
            "case or wants to evaluate whether to take a case."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_first_name": {"type": "string", "description": "Client's first name"},
                "client_last_name": {"type": "string", "description": "Client's last name"},
                "employer_name": {"type": "string", "description": "Employer's name"},
                "job_title": {"type": "string", "description": "Client's job title"},
                "incident_description": {"type": "string", "description": "Description of what happened"},
                "incident_date": {"type": "string", "description": "Date of incident (YYYY-MM-DD)"},
                "termination_date": {"type": "string", "description": "Date of termination if applicable (YYYY-MM-DD)"},
                "protected_class": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Protected classes: race, sex, age, disability, religion, national_origin, sexual_orientation, gender_identity",
                },
                "adverse_actions": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Adverse actions: termination, demotion, harassment, retaliation, failure_to_accommodate",
                },
                "annual_salary": {"type": "number", "description": "Annual salary"},
                "dfeh_filed": {"type": "boolean", "description": "Whether DFEH complaint has been filed"},
                "right_to_sue": {"type": "boolean", "description": "Whether right-to-sue letter has been received"},
            },
            "required": ["client_first_name", "client_last_name", "incident_description"],
        },
    },
    # --- Discovery ---
    {
        "name": "generate_discovery",
        "description": (
            "Generate a discovery set for a case. Can create form interrogatories, special "
            "interrogatories, requests for production, requests for admission, deposition notices, "
            "or subpoenas. Use when the user asks to draft discovery or needs to propound discovery."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID to generate discovery for"},
                "set_type": {
                    "type": "string",
                    "description": "Type: form_interrogatories, special_interrogatories, rfp, rfa, deposition_notice, subpoena_duces_tecum",
                },
                "target_elements": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Specific prima facie elements to target (optional)",
                },
            },
            "required": ["case_id", "set_type"],
        },
    },
    # --- Motions ---
    {
        "name": "draft_motion",
        "description": (
            "Draft a motion or pleading. Supports demurrers, motions to compel, MSJ/MSA, "
            "motions in limine, motions to strike, ex parte applications, complaints, "
            "oppositions, and replies. Auto-calculates hearing dates and filing deadlines."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID"},
                "motion_type": {
                    "type": "string",
                    "description": "Type: complaint, demurrer, motion_to_compel, msj, msa, motion_in_limine, motion_to_strike, ex_parte, opposition, reply, motion_for_sanctions",
                },
                "filing_party": {"type": "string", "description": "plaintiff or defendant"},
                "additional_context": {"type": "string", "description": "Additional context or instructions"},
            },
            "required": ["case_id", "motion_type"],
        },
    },
    # --- Oversight ---
    {
        "name": "motion_oversight",
        "description": (
            "Run the oversight agent on a case to identify motion opportunities, "
            "upcoming deadlines, strategic recommendations, and potential vulnerabilities. "
            "Use when the user asks about case strategy or what motions should be filed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID to analyze"},
            },
            "required": ["case_id"],
        },
    },
    # --- Contract Review ---
    {
        "name": "review_contract",
        "description": (
            "Review a contract for risk flags, missing clauses, and redline suggestions. "
            "Supports NDAs, protective orders, settlement agreements, and employment agreements. "
            "Use when the user wants to review or analyze a contract."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_text": {"type": "string", "description": "The full text of the contract"},
                "contract_type": {
                    "type": "string",
                    "description": "Type: nda, protective_order, settlement_agreement, employment_agreement",
                },
                "case_id": {"type": "string", "description": "Optional case ID if contract is case-related"},
                "reviewing_for": {"type": "string", "description": "Perspective: plaintiff or defendant"},
            },
            "required": ["contract_text", "contract_type"],
        },
    },
    # --- Deposition Prep ---
    {
        "name": "depo_prep",
        "description": (
            "Generate deposition preparation materials. Creates outlines for taking or "
            "defending depositions, with areas of inquiry, key questions, and strategic notes. "
            "Also supports depo practice sessions and transcript analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID"},
                "deponent_name": {"type": "string", "description": "Name of the deponent"},
                "deponent_role": {"type": "string", "description": "Role: plaintiff, defendant, witness, expert, corporate_designee"},
                "depo_type": {"type": "string", "description": "taking (you're deposing them) or defending (your client is being deposed)"},
                "areas_of_inquiry": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Specific areas to focus on (optional)",
                },
            },
            "required": ["case_id", "deponent_name", "deponent_role"],
        },
    },
    # --- Case Valuation ---
    {
        "name": "valuate_case",
        "description": (
            "Generate a data-driven case valuation using comparable verdicts and settlements "
            "from the verdict library. Provides estimated value range, comparable analysis, "
            "damages breakdown, and settlement recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID to valuate"},
            },
            "required": ["case_id"],
        },
    },
    # --- Calendar ---
    {
        "name": "get_deadlines",
        "description": (
            "Get upcoming deadlines and calendar events. Shows deadlines across all cases "
            "or for a specific case, with urgency classification and color coding."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Optional case ID to scope deadlines"},
                "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 30)"},
            },
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

    capabilities = """

## Document Intelligence
You have access to documents uploaded to cases. When users ask about specific
facts, testimony, contract terms, or evidence, use the search_case_documents
tool to find relevant excerpts. Always cite the source document and page number.

## Full Litigation Lifecycle
You manage the complete litigation lifecycle. Your capabilities include:

**Intake & Screening**: Use `analyze_intake` to evaluate potential cases. You identify
causes of action, map facts to prima facie elements (green checkmark = satisfied,
red flag = needs attention), check statute of limitations, and flag fatal affirmative
defenses. When a case is greenlighted, everything flows from the intake data.

**Complaint Generation**: Use `draft_motion` with type "complaint" to auto-generate
complaints from intake data. The complaint is the central document from which all
dates, discovery, and strategy flow.

**Discovery**: Use `generate_discovery` to draft discovery sets. At complaint filing,
you auto-generate the offensive package (Form Interrogatories, Special Interrogatories,
RFPs, RFAs). As new information enters the case, discovery is automatically updated.

**Law & Motion**: Use `draft_motion` for any motion type. Use `motion_oversight` to
proactively identify motion opportunities and deadlines.

**Contract Review**: Use `review_contract` for NDAs, protective orders, settlement
agreements, and employment agreements. Identifies risks, missing clauses, and
generates redline suggestions.

**Deposition Prep**: Use `depo_prep` to generate deposition outlines for taking or
defending depositions. Supports practice sessions and transcript analysis.

**Case Valuation**: Use `valuate_case` for data-driven valuations using comparable
verdicts and settlements from the library.

**Calendar**: Use `get_deadlines` to show upcoming deadlines with urgency levels.
All deadlines are auto-computed from case events (filings, discovery, motions).
"""

    return base + firm_section + capabilities


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

    # --- Intake Analysis ---
    if name == "analyze_intake":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.intake.engine import IntakeAnalyzer
            analyzer = IntakeAnalyzer(supabase_client=supabase)
            analysis = await analyzer.analyze_intake(input_data)
            if org_id:
                await analyzer.save_intake(
                    intake_data=input_data,
                    analysis=analysis,
                    org_id=org_id,
                    user_id=context.get("user_id"),
                )
            return {"status": "success", **analysis}
        except Exception as e:
            return {"status": "error", "message": f"Intake analysis failed: {e}"}

    # --- Discovery Generation ---
    if name == "generate_discovery":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.discovery.generator import DiscoveryGenerator
            gen = DiscoveryGenerator(supabase_client=supabase)
            result = await gen.generate_discovery_set(
                case_id=input_data["case_id"],
                org_id=org_id or "",
                set_type=input_data["set_type"],
                target_elements=input_data.get("target_elements", []),
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Discovery generation failed: {e}"}

    # --- Motion Drafting ---
    if name == "draft_motion":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.motions.engine import MotionEngine
            engine = MotionEngine(supabase_client=supabase)
            if input_data["motion_type"] == "complaint":
                result = await engine.generate_complaint(
                    case_id=input_data["case_id"],
                    org_id=org_id or "",
                )
            else:
                result = await engine.draft_motion(
                    case_id=input_data["case_id"],
                    org_id=org_id or "",
                    motion_type=input_data["motion_type"],
                    filing_party=input_data.get("filing_party", "plaintiff"),
                    additional_context=input_data.get("additional_context", ""),
                )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Motion drafting failed: {e}"}

    # --- Motion Oversight ---
    if name == "motion_oversight":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.motions.engine import MotionEngine
            engine = MotionEngine(supabase_client=supabase)
            result = await engine.oversight_analysis(
                case_id=input_data["case_id"],
                org_id=org_id or "",
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Oversight analysis failed: {e}"}

    # --- Contract Review ---
    if name == "review_contract":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.contracts.reviewer import ContractReviewer
            reviewer = ContractReviewer(supabase_client=supabase)
            result = await reviewer.review_contract(
                contract_text=input_data["contract_text"],
                contract_type=input_data["contract_type"],
                case_id=input_data.get("case_id"),
                org_id=org_id,
                reviewing_for=input_data.get("reviewing_for", "plaintiff"),
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Contract review failed: {e}"}

    # --- Deposition Prep ---
    if name == "depo_prep":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.deposition.prep import DepositionPrep
            prep = DepositionPrep(supabase_client=supabase)
            result = await prep.generate_outline(
                case_id=input_data["case_id"],
                org_id=org_id or "",
                deponent_name=input_data["deponent_name"],
                deponent_role=input_data["deponent_role"],
                depo_type=input_data.get("depo_type", "taking"),
                areas_of_inquiry=input_data.get("areas_of_inquiry", []),
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Depo prep failed: {e}"}

    # --- Case Valuation ---
    if name == "valuate_case":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.verdicts.scraper import VerdictLibrary
            lib = VerdictLibrary(supabase_client=supabase)
            result = await lib.valuate_case(
                case_id=input_data["case_id"],
                org_id=org_id or "",
            )
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": f"Case valuation failed: {e}"}

    # --- Calendar / Deadlines ---
    if name == "get_deadlines":
        if not supabase:
            return {"status": "error", "message": "Database not available."}
        try:
            from src.calendar.engine import CalendarEngine
            cal = CalendarEngine(supabase_client=supabase)
            deadlines = cal.get_upcoming_deadlines(
                org_id=org_id or "",
                days_ahead=input_data.get("days_ahead", 30),
                case_id=input_data.get("case_id"),
            )
            return {"status": "success", "deadlines": deadlines, "count": len(deadlines)}
        except Exception as e:
            return {"status": "error", "message": f"Deadline retrieval failed: {e}"}

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
