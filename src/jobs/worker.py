"""
CaseCommand — Background Job Worker

Polls the Postgres-backed job queue and dispatches to registered handlers.
Runs as an asyncio background task inside the FastAPI process.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from typing import Callable

from src.jobs.queue import JobQueue

logger = logging.getLogger(__name__)


class JobWorker:
    """Background worker that processes jobs from the queue."""

    def __init__(self, queue: JobQueue, supabase_client):
        self.queue = queue
        self.db = supabase_client
        self.handlers: dict[str, Callable] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register(self, job_type: str, handler: Callable):
        """
        Register a handler function for a given job type.

        The handler signature should be::

            async def my_handler(job: dict, supabase_client) -> dict:
                ...  # return a result dict

        ``job`` is the full row from ``background_jobs`` (includes payload,
        org_id, user_id, etc.).  The return value is stored as the job result.
        """
        self.handlers[job_type] = handler
        logger.info("Registered handler for job type: %s", job_type)

    # ------------------------------------------------------------------
    # Process a single job
    # ------------------------------------------------------------------

    async def process_one(self) -> bool:
        """
        Try to claim and process one job.

        Returns ``True`` if a job was processed (successfully or not),
        ``False`` if no job was available.
        """
        job_types = list(self.handlers.keys()) if self.handlers else None
        job = await self.queue.claim_next(job_types=job_types)

        if not job:
            return False

        job_id = job["id"]
        job_type = job.get("job_type", "unknown")

        handler = self.handlers.get(job_type)
        if not handler:
            error_msg = f"No handler registered for job type: {job_type}"
            logger.error(error_msg)
            await self.queue.fail(job_id, error_msg)
            return True

        logger.info("Processing job %s  type=%s", job_id, job_type)

        try:
            result = await handler(job, self.db)
            await self.queue.complete(job_id, result or {})
        except Exception as exc:
            tb = traceback.format_exc()
            error_msg = f"{exc.__class__.__name__}: {exc}\n{tb}"
            logger.error("Job %s failed: %s", job_id, error_msg)
            await self.queue.fail(job_id, error_msg)

        return True

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_loop(self, poll_interval: float = 5.0):
        """
        Main worker loop — polls for jobs and processes them.

        Runs until ``self._running`` is set to ``False``.  Sleeps for
        *poll_interval* seconds between polls when the queue is empty.
        When a job is found, immediately checks for the next one (no delay).
        """
        self._running = True
        logger.info(
            "Job worker started  handlers=%s  poll=%.1fs",
            list(self.handlers.keys()),
            poll_interval,
        )

        while self._running:
            try:
                processed = await self.process_one()
                if not processed:
                    # Queue empty — back off
                    await asyncio.sleep(poll_interval)
            except Exception as exc:
                # Catch-all so the loop never dies
                logger.error("Worker loop error: %s", exc)
                await asyncio.sleep(poll_interval)

    def stop(self):
        """Signal the worker loop to stop after the current iteration."""
        self._running = False
        logger.info("Job worker stop requested")
