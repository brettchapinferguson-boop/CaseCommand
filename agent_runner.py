"""
CaseCommand Agent Team Runner

Runs 10 specialized AI agents in parallel. Each agent analyzes the codebase,
legal knowledge, or system state and writes its output to Supabase.

Usage:
    python agent_runner.py              # Run all agents
    python agent_runner.py --agent=3    # Run a single agent by number

Designed to be called nightly by GitHub Actions (daily-evolution.yml).
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 4096
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

# ---------------------------------------------------------------------------
# Agent definitions — each has a name, role, and prompt
# ---------------------------------------------------------------------------

AGENTS = [
    {
        "name": "CodeAuditor",
        "role": "Senior Code Reviewer",
        "output_type": "code_fix",
        "priority": "high",
        "prompt": (
            "You are a senior Python/FastAPI code reviewer. Analyze the CaseCommand "
            "server.py and agent.py code below. Find bugs, security issues, performance "
            "problems, or code smells. For each issue, provide:\n"
            "1. File and approximate location\n"
            "2. The problem\n"
            "3. A specific fix (show the corrected code)\n\n"
            "Focus on real, actionable issues. Skip style nits."
        ),
    },
    {
        "name": "SecuritySentinel",
        "role": "Application Security Engineer",
        "output_type": "analysis",
        "priority": "critical",
        "prompt": (
            "You are an application security engineer. Review the CaseCommand codebase "
            "for OWASP Top 10 vulnerabilities, auth bypasses, injection risks, and data "
            "exposure. For each finding, provide:\n"
            "1. Severity (Critical/High/Medium/Low)\n"
            "2. The vulnerability\n"
            "3. Proof of concept or attack scenario\n"
            "4. Remediation code\n\n"
            "Be thorough but only report real risks, not theoretical ones."
        ),
    },
    {
        "name": "PerformanceProfiler",
        "role": "Performance Engineer",
        "output_type": "suggestion",
        "priority": "normal",
        "prompt": (
            "You are a performance engineer. Analyze the CaseCommand server for "
            "performance bottlenecks, N+1 queries, missing caching opportunities, "
            "slow async patterns, and memory issues. Provide specific optimizations "
            "with before/after code snippets."
        ),
    },
    {
        "name": "TestArchitect",
        "role": "QA & Test Engineer",
        "output_type": "code_fix",
        "priority": "normal",
        "prompt": (
            "You are a test architect. Review the CaseCommand codebase and identify "
            "the most critical untested paths. Write 3-5 pytest test functions that "
            "would provide the highest value coverage. Use pytest-asyncio for async "
            "tests. Include proper mocking of the Supabase client and Anthropic API."
        ),
    },
    {
        "name": "CaliforniaLawUpdater",
        "role": "California Legal Research Analyst",
        "output_type": "knowledge",
        "priority": "high",
        "prompt": (
            "You are a California legal research analyst. Review CaseCommand's SOUL.md "
            "and identify any California law areas where the system prompt could be "
            "improved or updated. Focus on:\n"
            "1. Recent CCP amendments or new rules\n"
            "2. Key case law updates in PI, employment, and civil litigation\n"
            "3. Deadline calculation rules that should be encoded\n"
            "4. Discovery-specific rules (CCP 2030-2033) updates\n\n"
            "Provide specific text additions for SOUL.md."
        ),
    },
    {
        "name": "PromptOptimizer",
        "role": "Prompt Engineering Specialist",
        "output_type": "suggestion",
        "priority": "normal",
        "prompt": (
            "You are a prompt engineering specialist for Claude. Review the CaseCommand "
            "system prompt (SOUL.md) and agent tool definitions. Suggest improvements to:\n"
            "1. Reduce token usage while maintaining quality\n"
            "2. Improve tool-calling reliability\n"
            "3. Add better guardrails or edge case handling\n"
            "4. Improve document drafting quality\n\n"
            "Provide specific before/after prompt text."
        ),
    },
    {
        "name": "UXEnhancer",
        "role": "Frontend UX Engineer",
        "output_type": "suggestion",
        "priority": "normal",
        "prompt": (
            "You are a UX engineer specializing in legal tech. Review the CaseCommand "
            "index.html frontend. Suggest 3-5 specific UI/UX improvements that would "
            "make the app more useful for a solo litigation attorney. For each, provide:\n"
            "1. The improvement\n"
            "2. Why it matters for a litigator\n"
            "3. Implementation snippet (HTML/CSS/JS)\n\n"
            "Focus on workflow improvements, not visual polish."
        ),
    },
    {
        "name": "APIHardener",
        "role": "API Reliability Engineer",
        "output_type": "code_fix",
        "priority": "high",
        "prompt": (
            "You are an API reliability engineer. Review CaseCommand's FastAPI server "
            "for error handling gaps, missing validation, timeout issues, and robustness "
            "problems. Provide specific fixes for:\n"
            "1. Endpoints that could crash on bad input\n"
            "2. Missing error responses or status codes\n"
            "3. Timeout and retry logic for external API calls\n"
            "4. Rate limiting or abuse prevention gaps"
        ),
    },
    {
        "name": "DocumentDrafter",
        "role": "Legal Document Quality Analyst",
        "output_type": "knowledge",
        "priority": "normal",
        "prompt": (
            "You are a legal document drafting specialist. Review CaseCommand's document "
            "generation code (build_docx function and DOCUMENT_FORMAT_INSTRUCTIONS). "
            "Suggest improvements to:\n"
            "1. Document formatting quality (legal standards)\n"
            "2. Missing document types that a PI/employment attorney needs\n"
            "3. Template improvements for meet-and-confer letters\n"
            "4. Better handling of legal citations and formatting\n\n"
            "Provide specific code changes and template text."
        ),
    },
    {
        "name": "FeatureScout",
        "role": "Product Strategy Analyst",
        "output_type": "suggestion",
        "priority": "normal",
        "prompt": (
            "You are a legal tech product strategist. Based on CaseCommand's current "
            "capabilities (chat, case management, document drafting, discovery analysis, "
            "trial outlines, settlement assessment), identify the top 3 features that "
            "would provide the most value to a solo litigator. For each:\n"
            "1. Feature name and description\n"
            "2. Why it's high-impact for Brett's practice\n"
            "3. Technical approach (API endpoints, DB schema, UI)\n"
            "4. Estimated complexity (small/medium/large)"
        ),
    },
]


# ---------------------------------------------------------------------------
# Codebase loader — reads key files for agent context
# ---------------------------------------------------------------------------

def load_codebase_context() -> str:
    """Read key source files to provide as context to agents."""
    root = Path(__file__).parent
    files_to_read = [
        "server.py",
        "src/agent.py",
        "src/api_client.py",
        "SOUL.md",
        "requirements.txt",
        "database/schema.sql",
    ]
    context_parts = []
    for fname in files_to_read:
        fpath = root / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            # Truncate very large files
            if len(content) > 15000:
                content = content[:15000] + "\n... [truncated]"
            context_parts.append(f"=== {fname} ===\n{content}")

    # index.html is huge — only include first portion
    index_path = root / "index.html"
    if index_path.exists():
        html = index_path.read_text(encoding="utf-8")
        context_parts.append(f"=== index.html (first 8000 chars) ===\n{html[:8000]}\n... [truncated]")

    return "\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

async def call_claude(system: str, user_message: str) -> str:
    """Call the Anthropic Messages API and return the text response."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": system,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(
            block["text"] for block in data.get("content", []) if block.get("type") == "text"
        )


# ---------------------------------------------------------------------------
# Supabase writer
# ---------------------------------------------------------------------------

async def write_to_supabase(agent: dict, title: str, content: str) -> bool:
    """Insert an agent output row into Supabase."""
    row = {
        "agent_name": agent["name"],
        "agent_role": agent["role"],
        "output_type": agent["output_type"],
        "title": title,
        "content": content,
        "priority": agent.get("priority", "normal"),
        "run_id": RUN_ID,
        "status": "pending",
        "metadata": json.dumps({
            "model": MODEL,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/agent_outputs",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=row,
        )
        if resp.status_code in (200, 201):
            return True
        print(f"  [!] Supabase write failed for {agent['name']}: {resp.status_code} {resp.text}")
        return False


# ---------------------------------------------------------------------------
# Telegram notifier
# ---------------------------------------------------------------------------

async def send_telegram_summary(results: list[dict]):
    """Send a summary of the agent run to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[*] Telegram not configured — skipping notification")
        return

    success = sum(1 for r in results if r["success"])
    total = len(results)
    lines = [
        f"🤖 *Agent Team Run Complete*",
        f"Run ID: `{RUN_ID}`",
        f"Results: {success}/{total} agents succeeded\n",
    ]
    for r in results:
        icon = "✅" if r["success"] else "❌"
        lines.append(f"{icon} *{r['name']}* — {r['title'][:60]}")

    text = "\n".join(lines)

    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
            },
        )


# ---------------------------------------------------------------------------
# Single agent runner
# ---------------------------------------------------------------------------

async def run_agent(agent: dict, codebase: str) -> dict:
    """Run a single agent and store its output."""
    name = agent["name"]
    print(f"  [{name}] Starting...")

    try:
        response = await call_claude(
            system=agent["prompt"],
            user_message=f"Here is the CaseCommand codebase to analyze:\n\n{codebase}",
        )

        # Extract a title from the first line of the response
        first_line = response.strip().split("\n")[0][:120]
        title = first_line.lstrip("#- ").strip() or f"{name} analysis"

        stored = await write_to_supabase(agent, title, response)
        status = "stored" if stored else "failed_to_store"
        print(f"  [{name}] Done — {status}")

        return {"name": name, "title": title, "success": stored}

    except Exception as e:
        print(f"  [{name}] ERROR: {e}")
        return {"name": name, "title": f"Error: {e}", "success": False}


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def main():
    print(f"🤖 CaseCommand Agent Team — Run {RUN_ID}")
    print(f"   Model: {MODEL}")
    print(f"   Agents: {len(AGENTS)}")
    print()

    # Validate required env vars
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Check which agents to run
    single_agent = None
    for arg in sys.argv[1:]:
        if arg.startswith("--agent="):
            single_agent = int(arg.split("=")[1]) - 1

    agents_to_run = [AGENTS[single_agent]] if single_agent is not None else AGENTS

    # Load codebase context
    print("[*] Loading codebase context...")
    codebase = load_codebase_context()
    print(f"    Context size: {len(codebase):,} characters")
    print()

    # Run agents in parallel (with concurrency limit to avoid rate limits)
    semaphore = asyncio.Semaphore(3)

    async def run_with_limit(agent):
        async with semaphore:
            return await run_agent(agent, codebase)

    print("[*] Running agents...")
    results = await asyncio.gather(*[run_with_limit(a) for a in agents_to_run])

    # Summary
    print()
    success = sum(1 for r in results if r["success"])
    print(f"✅ Complete: {success}/{len(results)} agents succeeded")

    # Send Telegram notification
    await send_telegram_summary(results)

    # Exit with error if any agent failed
    if success < len(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
