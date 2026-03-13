"""
╔══════════════════════════════════════════════════════════════╗
║  ARQ WORKER CONFIGURATION                                    ║
║                                                              ║
║  This file defines the WorkerSettings class that arq uses    ║
║  to configure the background worker process.                 ║
║                                                              ║
║  To start the worker:                                        ║
║    arq app.infrastructure.arq_worker.WorkerSettings          ║
║                                                              ║
║  The worker runs as a SEPARATE process from FastAPI.         ║
║  FastAPI enqueues jobs → Redis → Worker picks them up.       ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from arq.connections import RedisSettings
from app.application.tasks.email_tasks import send_welcome_email
from app.infrastructure.config import get_settings

logger = logging.getLogger("app.worker")


async def on_startup(ctx: dict):
    """
    Called when the arq worker starts up.

    LEARNING POINT:
    ─────────────────
    The ctx dict is shared across all job executions within
    this worker process. We load Settings here ONCE, and every
    task can access it via ctx['settings'].

    This is similar to FastAPI's lifespan — initialize shared
    resources once, reuse across requests/jobs.
    """
    settings = get_settings()
    ctx["settings"] = settings
    logger.info(f"🏭 Worker started for {settings.app_name}")
    logger.info(f"📧 SMTP configured: {settings.smtp_host}:{settings.smtp_port}")


async def on_shutdown(ctx: dict):
    """Called when the arq worker shuts down."""
    logger.info("🏭 Worker shutting down...")


class WorkerSettings:
    """
    arq worker configuration.

    HOW THIS WORKS:
    ─────────────────
    1. `functions` — list of async functions the worker can execute
    2. `on_startup` — runs once when worker starts (load settings, etc.)
    3. `on_shutdown` — runs once when worker stops (cleanup)
    4. `redis_settings` — how to connect to Redis
    5. `max_jobs` — max concurrent jobs (prevents overload)
    6. `job_timeout` — max time per job (prevents hanging)

    START THE WORKER:
        arq app.infrastructure.arq_worker.WorkerSettings
    """

    # ── Task functions the worker can execute ──
    functions = [send_welcome_email]

    # ── Lifecycle hooks ──
    on_startup = on_startup
    on_shutdown = on_shutdown

    # ── Redis connection ──
    # Reads from Settings (which reads from .env)
    _settings = get_settings()
    redis_settings = RedisSettings(
        host=_settings.redis_host,
        port=_settings.redis_port,
        password=_settings.redis_password,
    )

    # ── Worker behavior ──
    max_jobs = 10               # Max concurrent jobs
    job_timeout = 300           # 5 minutes max per job
    retry_jobs = True           # Retry failed jobs
    allow_abort_jobs = True     # Allow job cancellation
