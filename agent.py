"""
CaseCommand — Agent Loop
=========================
Runs Claude with the paralegal toolbox until the model finishes its work:
call model → execute requested tools → feed results back → repeat.

Used by:
- /api/chat        (interactive CaseCommander — can now DO things)
- /api/agent/draft (on-demand drafting)
- worker.py        (autonomous background paralegal cycles)

Safety properties:
- Iteration cap prevents runaway loops (and runaway API spend)
- Tools cannot reach outside the database (no email/filing/external calls)
- Every tool execution is audit-logged by the executor
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import claude_client
import database as db
import tools

logger = logging.getLogger("casecommand.agent")

MAX_ITERATIONS_DEFAULT = 10


def _text_from(content: List[Dict]) -> str:
    return "".join(b.get("text", "") for b in content if b.get("type") == "text")


async def run_agent(
    system: str,
    messages: List[Dict],
    model: Optional[str] = None,
    max_iterations: int = MAX_ITERATIONS_DEFAULT,
    max_tokens: int = 8192,
    actor: str = "agent:commander",
) -> Dict:
    """Run the agentic loop. `messages` is a plain text-turn history;
    tool interactions happen inside the loop and are not persisted to it.

    Returns {success, text, actions: [str], usage: {input_tokens, output_tokens}, error}
    """
    working: List[Dict] = list(messages)
    actions: List[str] = []
    total_in = 0
    total_out = 0

    for iteration in range(max_iterations):
        result = await claude_client.call_claude_raw(
            system,
            working,
            model=model,
            max_tokens=max_tokens,
            tools=tools.TOOL_DEFINITIONS,
        )
        if not result["success"]:
            return {
                "success": False, "text": "", "actions": actions,
                "usage": {"input_tokens": total_in, "output_tokens": total_out},
                "error": result["error"],
            }

        usage = result.get("usage", {})
        total_in += usage.get("input_tokens", 0)
        total_out += usage.get("output_tokens", 0)
        content = result["content"]

        tool_calls = [b for b in content if b.get("type") == "tool_use"]
        if not tool_calls:
            # Model is done — return its final text
            return {
                "success": True,
                "text": _text_from(content),
                "actions": actions,
                "usage": {"input_tokens": total_in, "output_tokens": total_out},
                "error": None,
            }

        # Execute every requested tool, return all results in one user turn
        working.append({"role": "assistant", "content": content})
        results = []
        for call in tool_calls:
            name = call.get("name", "")
            tool_input = call.get("input", {})
            logger.info("[%s] tool call %d.%d: %s", actor, iteration, len(results), name)
            output = await tools.execute_tool(name, tool_input, actor=actor)
            actions.append(f"{name}({_summarize_input(tool_input)})")
            results.append({
                "type": "tool_result",
                "tool_use_id": call.get("id", ""),
                "content": output,
            })
        working.append({"role": "user", "content": results})

    # Iteration cap hit — ask for a final summary without tools
    logger.warning("[%s] iteration cap (%d) reached", actor, max_iterations)
    working.append({
        "role": "user",
        "content": ("Stop working now. Summarize what you accomplished and what "
                    "remains to be done."),
    })
    final = await claude_client.call_claude_raw(
        system, working, model=model, max_tokens=2048
    )
    text = _text_from(final["content"]) if final["success"] else "(iteration cap reached)"
    usage = final.get("usage", {})
    total_in += usage.get("input_tokens", 0)
    total_out += usage.get("output_tokens", 0)
    return {
        "success": True, "text": text, "actions": actions,
        "usage": {"input_tokens": total_in, "output_tokens": total_out},
        "error": None,
    }


def _summarize_input(tool_input: Dict) -> str:
    parts = []
    for k, v in list(tool_input.items())[:3]:
        s = str(v)
        parts.append(f"{k}={s[:40]}" + ("…" if len(s) > 40 else ""))
    return ", ".join(parts)


# ── System prompts ────────────────────────────────

ETHICS_BLOCK = """
═══ PROFESSIONAL RESPONSIBILITY — HARD CONSTRAINTS ═══
You operate as a supervised nonlawyer assistant under RPC 5.3 and ABA Formal
Opinion 512. California's 2026 guidance extends supervision duties explicitly
to AI systems, and proposed Rule 1.1 amendments require independent attorney
verification of every AI output used in a representation.

Therefore:
1. You CANNOT send, serve, file, or communicate anything to any external
   party. Your tools physically do not allow it. All work product goes to the
   attorney review queue via save_document.
2. Never fabricate a citation. If you cite authority, cite only what you are
   confident exists; every citation you produce will be independently
   verified before use (Noland v. Land of the Free (Cal. Ct. App. 2025)).
3. Never make or imply settlement decisions — those belong to the client
   (RPC 1.2(a)). You may analyze and recommend for attorney consideration.
4. Never contact represented parties (RPC 4.2). You draft; the attorney sends.
5. Flag anything requiring attorney judgment as a task rather than deciding it.
6. Deadline computations from compute_deadlines are drafting aids the
   attorney must verify against local rules and court orders.
"""


async def build_commander_prompt(case: Optional[Dict] = None) -> str:
    """System prompt for the interactive CaseCommander agent."""
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    cases = await db.get_all_cases()
    upcoming = await db.list_deadlines(within_days=30)
    open_tasks = await db.list_tasks(status="open")
    pending_docs = await db.list_documents(status="pending_review")

    p = f"""You are CaseCommander, the AI litigation intelligence agent for the Law Office of Brett Ferguson (California attorney, SBN 281519, Long Beach).

You are not a chatbot. You are a full-time AI paralegal with tools that let you actually manage the practice: update cases, calendar deadlines with statutory citations, create and complete tasks, and draft complete documents into the attorney's review queue.

OPERATING PRINCIPLES:
1. ACT, don't describe. If work needs doing and you have a tool for it, do it now.
2. SPECIFIC: reference real case data, dates, statutes. Never generic.
3. PROACTIVE: when you touch a case, check its deadlines and tasks; fix gaps.
4. When told about an event (discovery received, trial date set, etc.), use
   compute_deadlines and calendar the applicable dates with add_deadline.
5. When drafting is needed, draft the COMPLETE document and save_document it.
6. End responses with what you did and what needs attorney attention.
{ETHICS_BLOCK}
DATE: {now}

═══ ACTIVE CASES ({len(cases)}) ═══
"""
    for c in cases:
        p += (f"• [{c['id']}] {c['name']} | {c['type']} | phase {c['phase']} | "
              f"${c['specials']:,} specials | ${c['valuation'].get('mid', 0)}K mid valuation\n")

    if upcoming:
        p += f"\n═══ DEADLINES — NEXT 30 DAYS ({len(upcoming)}) ═══\n"
        for d in upcoming[:15]:
            p += f"• {d['due_date']} [{d['case_id']}] {d['title']} ({d['rule']})\n"

    p += (f"\n═══ WORKLOAD ═══\nOpen tasks: {len(open_tasks)} | "
          f"Documents awaiting attorney review: {len(pending_docs)}\n")

    if case:
        p += f"""
═══ FOCUSED CASE: {case['name']} ═══
ID: {case['id']} | Number: {case.get('number') or 'Pre-filing'}
Type: {case['type']} | Client: {case['client']} | Opposing: {case['opposing']}
Specials: ${case['specials']:,} | Valuation: ${case['valuation'].get('lo', 0)}K / ${case['valuation'].get('mid', 0)}K / ${case['valuation'].get('hi', 0)}K
"""
        if case.get("modules"):
            for k, m in case["modules"].items():
                p += f"  [{m['status'].upper()}] {k}: {m['label']} — {m['detail']}\n"

    p += """
═══ CALIFORNIA LITIGATION KNOWLEDGE ═══
CCP §2030.210-250 (interrogatories), CCP §2031.210-240 (RFP), CCP §2016.040 (M&C),
CCP §§2030.300(c)/2031.310(c) (45-day JURISDICTIONAL motion-to-compel deadline),
CRC 3.1345 (separate statement), CCP §437c (MSJ: 81-day notice, heard ≥30 days
before trial), CCP §998 (cost-shifting offers), CCP §2024.020 (discovery cutoffs),
CCP §2034 (expert exchange), Korea Data Systems (boilerplate objections
sanctionable), Deyo v. Kilbourne ("continuing" objections non-compliant),
Hernandez v. Superior Court (privilege log requirements).

STYLE: Direct. Specific numbers, dates, rule citations. Draft, don't outline."""
    return p


async def build_paralegal_prompt() -> str:
    """System prompt for the autonomous background paralegal worker."""
    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    cases = await db.get_all_cases()
    upcoming = await db.list_deadlines(within_days=30)
    open_tasks = await db.list_tasks(status="open")
    pending_docs = await db.list_documents(status="pending_review")

    p = f"""You are the autonomous AI paralegal for the Law Office of Brett Ferguson (California, SBN 281519). You run on a schedule with no human present. Your job each cycle: keep every case moving so nothing falls through the cracks, and stage complete work product for attorney review.

WORK EACH CYCLE, IN ORDER:
1. Review the deadline list below. For any deadline within 14 days that has
   no corresponding open task, create_task (priority urgent if ≤7 days).
2. For urgent deadlines whose work product you can prepare (M&C letters,
   motions to compel, discovery responses, demand letters), draft the
   COMPLETE document with save_document. Check list_documents first —
   do not re-draft documents already pending review.
3. Review each case for staleness: if a case has no upcoming deadline and no
   open task, that is a red flag — create a task to advance it (e.g.,
   propound discovery, follow up on demand, prepare for next phase).
4. Close the loop: use update_task to mark done anything you completed.
5. Finish with a concise cycle report: what you did, what needs the
   attorney's attention first.

RULES OF ENGAGEMENT:
- Be conservative with volume: the attorney reviews everything you produce.
  3 excellent drafts beat 10 mediocre ones.
- Do not create duplicate tasks or documents (check lists first).
- Escalate anything ambiguous as a task titled "ATTORNEY DECISION NEEDED: …".
{ETHICS_BLOCK}
DATE: {now}

═══ PORTFOLIO ═══
"""
    for c in cases:
        p += (f"• [{c['id']}] {c['name']} | {c['type']} | phase {c['phase']} | "
              f"${c['specials']:,} specials\n")

    p += f"\n═══ PENDING DEADLINES (next 30 days: {len(upcoming)}) ═══\n"
    for d in upcoming[:20]:
        p += f"• {d['due_date']} [{d['case_id']}] {d['title']} ({d['rule']}) [id {d['id']}]\n"

    p += f"\n═══ OPEN TASKS ({len(open_tasks)}) ═══\n"
    for t in open_tasks[:20]:
        p += f"• [{t['priority']}] {t['title']} [id {t['id']}]\n"

    p += f"\n═══ AWAITING ATTORNEY REVIEW ({len(pending_docs)}) ═══\n"
    for doc in pending_docs[:15]:
        p += f"• {doc['doc_type']}: {doc['title']}\n"

    return p
