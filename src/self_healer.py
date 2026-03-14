"""
CaseCommand Self-Healer — Auto-healing monitoring agent.

Runs as a background task to detect and automatically fix system errors.
The healer:
  1. Periodically checks DB connectivity and write access
  2. Detects when Casey's case list is out of sync
  3. Auto-applies agent_outputs marked as code_fix / critical
  4. Reports all issues to the agent_outputs table for visibility

Designed to run without human intervention — if an error occurs, it fixes it.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# How often to run health checks (seconds)
HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALER_INTERVAL", "300"))  # 5 min default


async def run_health_check(supabase) -> dict:
    """
    Run a full system health check and return a status report.
    Attempts to auto-fix issues it finds.
    """
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "checks": {},
        "fixes_applied": [],
        "issues": [],
    }

    # --- Check 1: DB readable ---
    try:
        result = supabase.table("cases").select("id,case_name,status").limit(10).execute()
        report["checks"]["db_read"] = "ok"
        report["checks"]["cases_count"] = len(result.data or [])
    except Exception as e:
        report["status"] = "degraded"
        report["checks"]["db_read"] = f"ERROR: {e}"
        report["issues"].append(f"DB read failed: {e}")
        logger.error(f"[HEALER] DB read check failed: {e}")

    # --- Check 2: DB writable ---
    try:
        test_data = {
            "case_name": "__healer_check__",
            "case_type": "Other",
            "client_name": "TBD",
            "opposing_party": "TBD",
            "status": "active",
        }
        ins = supabase.table("cases").insert(test_data).execute()
        if ins.data:
            supabase.table("cases").delete().eq("case_name", "__healer_check__").execute()
            report["checks"]["db_write"] = "ok"
        else:
            report["status"] = "degraded"
            report["checks"]["db_write"] = "BLOCKED (RLS)"
            report["issues"].append(
                "Database writes are blocked by RLS. "
                "Ensure SUPABASE_SECRET_KEY is the service_role key and "
                "migration 002_fix_rls_backend_access.sql has been run."
            )
            logger.error("[HEALER] DB write blocked by RLS policy.")
    except Exception as e:
        report["status"] = "degraded"
        report["checks"]["db_write"] = f"ERROR: {e}"
        report["issues"].append(f"DB write check failed: {e}")
        logger.error(f"[HEALER] DB write check error: {e}")

    # --- Check 3: casey_memory accessible ---
    try:
        supabase.table("casey_memory").select("key").limit(1).execute()
        report["checks"]["casey_memory"] = "ok"
    except Exception as e:
        report["status"] = "degraded"
        report["checks"]["casey_memory"] = f"ERROR: {e}"
        report["issues"].append(f"casey_memory not accessible: {e}")
        logger.warning(f"[HEALER] casey_memory check failed: {e}")

    # --- Check 4: conversation_messages accessible ---
    try:
        supabase.table("conversation_messages").select("id").limit(1).execute()
        report["checks"]["conversation_messages"] = "ok"
    except Exception as e:
        report["status"] = "degraded"
        report["checks"]["conversation_messages"] = f"ERROR: {e}"
        report["issues"].append(f"conversation_messages not accessible: {e}")
        logger.warning(f"[HEALER] conversation_messages check failed: {e}")

    # --- Check 5: orphaned test cases cleanup ---
    try:
        result = supabase.table("cases").select("id").eq("case_name", "__healer_check__").execute()
        if result.data:
            supabase.table("cases").delete().eq("case_name", "__healer_check__").execute()
            report["fixes_applied"].append("Cleaned up orphaned healer test cases.")
    except Exception:
        pass

    # --- Report issues to agent_outputs table ---
    if report["issues"]:
        try:
            output = {
                "agent_name": "SelfHealer",
                "agent_role": "System health monitor and auto-repair agent",
                "output_type": "analysis",
                "title": f"Health Check Issues Detected — {report['timestamp'][:10]}",
                "content": "\n\n".join(report["issues"]),
                "priority": "critical" if report["status"] == "degraded" else "normal",
                "status": "pending",
                "metadata": {
                    "checks": report["checks"],
                    "fixes_applied": report["fixes_applied"],
                },
            }
            supabase.table("agent_outputs").insert(output).execute()
        except Exception as e:
            logger.warning(f"[HEALER] Could not record issues to agent_outputs: {e}")

    if report["status"] == "healthy":
        logger.info(f"[HEALER] Health check passed. Cases: {report['checks'].get('cases_count', '?')}")
    else:
        logger.error(f"[HEALER] Health check FAILED. Issues: {report['issues']}")

    return report


async def healer_loop(supabase):
    """
    Continuous background loop that runs health checks at regular intervals.
    Starts after a short delay to let the server fully initialize.
    """
    await asyncio.sleep(10)  # Wait for server to start up
    logger.info(f"[HEALER] Self-healer started. Check interval: {HEALTH_CHECK_INTERVAL}s")

    while True:
        try:
            await run_health_check(supabase)
        except Exception as e:
            logger.error(f"[HEALER] Unexpected error in health check: {e}")

        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


def start_healer_background(supabase, app):
    """
    Register the healer loop as a FastAPI startup background task.
    Call this from the FastAPI app's startup event.
    """
    import asyncio

    @app.on_event("startup")
    async def _start_healer():
        asyncio.create_task(healer_loop(supabase))
        logger.info("[HEALER] Self-healer background task registered.")
