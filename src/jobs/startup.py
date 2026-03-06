"""
CaseCommand — Job Worker Startup

Integrates the background job worker with FastAPI's application lifecycle.
Call ``start_job_worker(app)`` from your app startup event or lifespan.
"""

from __future__ import annotations

import asyncio
import logging

from src.jobs.queue import JobQueue
from src.jobs.worker import JobWorker
from src.jobs.handlers import (
    handle_extract_text,
    handle_generate_embeddings,
    handle_process_file,
)

logger = logging.getLogger(__name__)


async def start_job_worker(app):
    """
    Register job handlers and start the worker loop as a background task.

    Attaches the worker and queue to ``app.state`` so routes can enqueue
    jobs via ``request.app.state.job_queue``.

    Usage in server.py::

        @app.on_event("startup")
        async def on_startup():
            from src.jobs.startup import start_job_worker
            await start_job_worker(app)
    """
    supabase = app.state.supabase

    # Create queue and attach to app state so routes can enqueue jobs
    queue = JobQueue(supabase)
    app.state.job_queue = queue

    # Create worker with registered handlers
    worker = JobWorker(queue, supabase)
    worker.register("extract_text", handle_extract_text)
    worker.register("generate_embeddings", handle_generate_embeddings)
    worker.register("process_file", handle_process_file)
    app.state.job_worker = worker

    # Launch the worker loop as a fire-and-forget background task
    task = asyncio.create_task(worker.run_loop(poll_interval=5.0))
    app.state._job_worker_task = task

    logger.info("Background job worker started")


async def stop_job_worker(app):
    """
    Gracefully stop the job worker.

    Call from a shutdown event::

        @app.on_event("shutdown")
        async def on_shutdown():
            from src.jobs.startup import stop_job_worker
            await stop_job_worker(app)
    """
    worker: JobWorker | None = getattr(app.state, "job_worker", None)
    if worker:
        worker.stop()

    task: asyncio.Task | None = getattr(app.state, "_job_worker_task", None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("Background job worker stopped")
