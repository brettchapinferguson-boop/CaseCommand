"""
CaseCommand — Autonomous Paralegal Worker
==========================================
Background scheduler that runs paralegal cycles without being asked:

- Deterministic deadline sweep (no AI): any pending deadline within 14 days
  gets an open task; ≤7 days is urgent. This safety net runs even if the
  AI layer is down or no API key is configured.
- Agentic cycle (AI): the paralegal agent reviews the portfolio with tools,
  creates/completes tasks, and drafts documents into the attorney review
  queue. Runs at PARALEGAL_INTERVAL seconds (default hourly; 0 disables).
- Daily digest: one AI-written practice digest per calendar day, saved as a
  reviewable document.

Everything lands in the database. Nothing is sent anywhere. Every cycle is
recorded in agent_runs and the audit log for supervision (RPC 5.3).
"""

import os
import uuid
import asyncio
import logging
from datetime import date, datetime
from typing import Dict, Optional

import agent
import database as db
import claude_client

logger = logging.getLogger("casecommand.worker")

PARALEGAL_INTERVAL = int(os.environ.get("PARALEGAL_INTERVAL", "3600"))
DIGEST_HOUR = int(os.environ.get("DIGEST_HOUR", "6"))  # earliest hour for daily digest
CYCLE_MAX_ITERATIONS = int(os.environ.get("CYCLE_MAX_ITERATIONS", "12"))

state: Dict = {
    "enabled": PARALEGAL_INTERVAL > 0,
    "running": False,
    "last_cycle_at": None,
    "last_cycle_summary": None,
    "cycles_completed": 0,
}

_task: Optional[asyncio.Task] = None


async def sweep_deadlines() -> int:
    """Deterministic safety net: ensure every near-term deadline has a task.
    Returns the number of tasks created."""
    created = 0
    upcoming = await db.list_deadlines(within_days=14)
    today = date.today()
    for dl in upcoming:
        if await db.task_exists_for(dl["case_id"], dl["title"][:40]):
            continue
        days_left = (date.fromisoformat(dl["due_date"]) - today).days
        priority = "urgent" if days_left <= 7 else "high"
        task = await db.create_task({
            "id": str(uuid.uuid4())[:8],
            "case_id": dl["case_id"],
            "title": f"Prepare for deadline: {dl['title'][:120]}",
            "detail": (f"Due {dl['due_date']} ({days_left} days). "
                       f"Rule: {dl['rule'] or 'n/a'}. {dl.get('note', '')}"),
            "priority": priority,
            "due_date": dl["due_date"],
            "created_by": "system:sweep",
        })
        await db.log_audit("system:sweep", "create_task", "task", task["id"],
                           f"Deadline sweep: {dl['title'][:80]}")
        created += 1
    if created:
        logger.info("Deadline sweep created %d tasks", created)
    return created


async def _digest_needed() -> bool:
    if datetime.now().hour < DIGEST_HOUR:
        return False
    docs = await db.list_documents(status="pending_review")
    docs += await db.list_documents(status="approved")
    today_iso = date.today().isoformat()
    return not any(
        d["doc_type"] == "digest" and d["created_at"].startswith(today_iso)
        for d in docs
    )


async def run_cycle(kind: str = "scheduled_cycle") -> Dict:
    """Run one full paralegal cycle. Returns a result summary dict."""
    run_id = str(uuid.uuid4())[:8]
    await db.start_agent_run(run_id, kind)
    state["running"] = True
    try:
        # 1. Deterministic sweep (works without AI)
        swept = await sweep_deadlines()

        # 2. Agentic cycle
        if not claude_client.API_KEY:
            summary = f"Deadline sweep only (no API key): {swept} tasks created"
            await db.finish_agent_run(run_id, "partial", summary, actions=swept)
            return {"run_id": run_id, "status": "partial", "summary": summary,
                    "actions": swept}

        system = await agent.build_paralegal_prompt()
        work_order = (
            "Run your paralegal cycle now. Work the portfolio per your "
            "instructions, then report."
        )
        if await _digest_needed():
            work_order += (
                " Also produce today's daily digest: save_document with "
                "doc_type 'digest', covering case statuses, deadlines, open "
                "tasks, and your recommendations for the attorney's day."
            )

        result = await agent.run_agent(
            system,
            [{"role": "user", "content": work_order}],
            model=claude_client.WORKER_MODEL,
            max_iterations=CYCLE_MAX_ITERATIONS,
            actor="agent:paralegal",
        )

        if result["success"]:
            summary = result["text"][:1500]
            status = "completed"
        else:
            summary = f"Agent error: {result['error']} (sweep created {swept} tasks)"
            status = "error"

        await db.finish_agent_run(
            run_id, status, summary,
            actions=len(result["actions"]) + swept,
            input_tokens=result["usage"]["input_tokens"],
            output_tokens=result["usage"]["output_tokens"],
        )
        return {"run_id": run_id, "status": status, "summary": summary,
                "actions": len(result["actions"]) + swept,
                "tool_calls": result["actions"]}
    except Exception as e:
        logger.exception("Paralegal cycle failed")
        await db.finish_agent_run(run_id, "error", str(e))
        return {"run_id": run_id, "status": "error", "summary": str(e), "actions": 0}
    finally:
        state["running"] = False
        state["last_cycle_at"] = datetime.now().isoformat()
        state["cycles_completed"] += 1


async def _loop():
    logger.info("Paralegal worker started (interval %ds, model %s)",
                PARALEGAL_INTERVAL, claude_client.WORKER_MODEL)
    while True:
        await asyncio.sleep(PARALEGAL_INTERVAL)
        try:
            result = await run_cycle()
            state["last_cycle_summary"] = result["summary"][:300]
            logger.info("Cycle %s: %s (%d actions)",
                        result["run_id"], result["status"], result["actions"])
        except Exception:
            logger.exception("Worker loop iteration failed")


def start() -> Optional[asyncio.Task]:
    """Start the background loop (call from app lifespan). Sleeps first,
    so startup is never blocked and tests never trigger cycles."""
    global _task
    if PARALEGAL_INTERVAL <= 0:
        logger.info("Paralegal worker disabled (PARALEGAL_INTERVAL=0)")
        return None
    _task = asyncio.create_task(_loop())
    return _task


async def stop():
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
