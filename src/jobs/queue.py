"""
CaseCommand — Postgres-Backed Job Queue

Lightweight async job queue backed by the ``background_jobs`` table.
Good enough for 50-100 firms; swap to Redis + Celery when needed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JobQueue:
    """Postgres-backed async job queue using the background_jobs table."""

    def __init__(self, supabase_client):
        self.db = supabase_client

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    async def enqueue(
        self,
        job_type: str,
        payload: dict,
        org_id: str,
        user_id: str | None = None,
        max_attempts: int = 3,
        scheduled_at: str | None = None,
    ) -> str:
        """
        Create a new job in the queue.

        Returns the job UUID.
        """
        row = {
            "job_type": job_type,
            "payload": payload,
            "org_id": org_id,
            "status": "pending",
            "max_attempts": max_attempts,
        }
        if user_id:
            row["user_id"] = user_id
        if scheduled_at:
            row["scheduled_at"] = scheduled_at

        result = self.db.table("background_jobs").insert(row).execute()
        job_id = result.data[0]["id"]
        logger.info("Enqueued job %s  type=%s  org=%s", job_id, job_type, org_id)
        return job_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_job(self, job_id: str) -> dict | None:
        """Get job status and result by ID."""
        result = (
            self.db.table("background_jobs")
            .select("*")
            .eq("id", job_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # Claim (atomic dequeue)
    # ------------------------------------------------------------------

    async def claim_next(self, job_types: list[str] | None = None) -> dict | None:
        """
        Atomically claim the next pending job.

        Uses an RPC call to perform ``UPDATE ... RETURNING`` so that
        concurrent workers don't grab the same job.  Falls back to a
        two-step select-then-update when the RPC is not available.

        Filters:
        - status = 'pending'
        - scheduled_at <= now()
        - attempts < max_attempts
        """
        now = datetime.now(timezone.utc).isoformat()

        # --- Try the RPC path first (requires a Postgres function) ---
        try:
            params: dict = {"p_now": now}
            if job_types:
                params["p_job_types"] = job_types
            result = self.db.rpc("claim_next_job", params).execute()
            if result.data:
                job = result.data[0] if isinstance(result.data, list) else result.data
                if job and job.get("id"):
                    logger.info("Claimed job %s (via RPC)  type=%s", job["id"], job.get("job_type"))
                    return job
        except Exception:
            # RPC not deployed yet — fall back to two-step approach
            pass

        # --- Fallback: select + update (small race window, acceptable at this scale) ---
        query = (
            self.db.table("background_jobs")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_at", now)
            .order("scheduled_at", desc=False)
            .limit(1)
        )
        if job_types:
            query = query.in_("job_type", job_types)

        result = query.execute()
        if not result.data:
            return None

        job = result.data[0]

        # Skip if already at max attempts
        if job.get("attempts", 0) >= job.get("max_attempts", 3):
            return None

        # Optimistic update — claim it
        update_result = (
            self.db.table("background_jobs")
            .update({
                "status": "running",
                "started_at": now,
                "attempts": job.get("attempts", 0) + 1,
            })
            .eq("id", job["id"])
            .eq("status", "pending")  # guard: only if still pending
            .execute()
        )

        if not update_result.data:
            # Another worker got it — return None so caller retries
            return None

        claimed = update_result.data[0]
        logger.info("Claimed job %s  type=%s", claimed["id"], claimed.get("job_type"))
        return claimed

    # ------------------------------------------------------------------
    # Complete / Fail
    # ------------------------------------------------------------------

    async def complete(self, job_id: str, result: dict) -> None:
        """Mark a job as completed with its result payload."""
        now = datetime.now(timezone.utc).isoformat()
        self.db.table("background_jobs").update({
            "status": "completed",
            "result": result,
            "completed_at": now,
        }).eq("id", job_id).execute()
        logger.info("Completed job %s", job_id)

    async def fail(self, job_id: str, error: str) -> None:
        """
        Mark a job as failed.

        If the job still has remaining attempts (attempts < max_attempts),
        set it back to ``pending`` so it will be retried.  Otherwise mark
        it as ``failed`` permanently.
        """
        job = await self.get_job(job_id)
        if not job:
            logger.warning("Cannot fail unknown job %s", job_id)
            return

        attempts = job.get("attempts", 1)
        max_attempts = job.get("max_attempts", 3)

        if attempts < max_attempts:
            # Retry — put back in queue
            self.db.table("background_jobs").update({
                "status": "pending",
                "error_message": error,
            }).eq("id", job_id).execute()
            logger.info(
                "Job %s failed (attempt %d/%d), re-queued: %s",
                job_id, attempts, max_attempts, error,
            )
        else:
            # Permanently failed
            now = datetime.now(timezone.utc).isoformat()
            self.db.table("background_jobs").update({
                "status": "failed",
                "error_message": error,
                "completed_at": now,
            }).eq("id", job_id).execute()
            logger.error(
                "Job %s permanently failed after %d attempts: %s",
                job_id, attempts, error,
            )
