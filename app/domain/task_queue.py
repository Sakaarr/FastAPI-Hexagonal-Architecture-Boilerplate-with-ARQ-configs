"""
╔══════════════════════════════════════════════════════════════╗
║  DOMAIN PORT: Task Queue Interface                           ║
║                                                              ║
║  This is an abstract contract that says "I can enqueue       ║
║  background tasks". The domain/application layers use this   ║
║  port — they never know if it's arq, Celery, or a fake.     ║
╚══════════════════════════════════════════════════════════════╝
"""

from abc import ABC, abstractmethod
from typing import Any


class TaskQueue(ABC):
    """
    Abstract port for enqueuing background tasks.

    WHY THIS EXISTS:
    ─────────────────
    The CreateUser use case needs to trigger a "send welcome email"
    task, but it shouldn't know HOW that task gets queued.

    - In production: ArqTaskQueue enqueues to Redis
    - In tests: FakeTaskQueue stores tasks in a list
    - Could also be: CeleryTaskQueue, SQSTaskQueue, etc.
    """

    @abstractmethod
    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str | None:
        """
        Enqueue a background task by name.

        Args:
            task_name: The registered name of the task function
            *args: Positional arguments to pass to the task
            **kwargs: Keyword arguments to pass to the task

        Returns:
            Job ID if successfully enqueued, None otherwise
        """
        pass
