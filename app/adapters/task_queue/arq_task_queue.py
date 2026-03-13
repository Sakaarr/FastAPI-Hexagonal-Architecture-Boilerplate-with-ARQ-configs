"""
╔══════════════════════════════════════════════════════════════╗
║  ADAPTER: Arq Task Queue Implementation                      ║
║                                                              ║
║  This implements the abstract TaskQueue port using arq        ║
║  (Redis-backed async job queue).                             ║
║                                                              ║
║  The use case calls:  task_queue.enqueue("send_welcome_email", ...)  ║
║  This adapter puts it into Redis → arq worker picks it up.   ║
╚══════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Any
from arq import ArqRedis
from app.domain.task_queue import TaskQueue

logger = logging.getLogger("app.tasks")


class ArqTaskQueue(TaskQueue):
    """
    Production implementation of TaskQueue using arq + Redis.

    HOW IT WORKS:
    ─────────────
    1. FastAPI app creates an ArqRedis pool on startup
    2. This adapter wraps that pool
    3. When enqueue() is called, it puts the job into Redis
    4. A separate arq worker process picks up the job and runs it

    The use case doesn't know any of this — it just calls
    task_queue.enqueue("send_welcome_email", email, name)
    """

    def __init__(self, pool: ArqRedis):
        self.pool = pool

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str | None:
        """
        Enqueue a job via arq.

        arq.enqueue_job expects:
          - 1st arg: function name (string)
          - remaining args: passed to the function
        """
        try:
            job = await self.pool.enqueue_job(task_name, *args, **kwargs)
            if job:
                logger.info(f"📨 Enqueued task '{task_name}' → job_id={job.job_id}")
                return job.job_id
            else:
                logger.warning(f"⚠️ Task '{task_name}' was not enqueued (possibly duplicate)")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to enqueue task '{task_name}': {e}")
            return None
