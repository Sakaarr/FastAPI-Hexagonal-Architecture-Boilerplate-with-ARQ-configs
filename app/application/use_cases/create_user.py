from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.task_queue import TaskQueue


class CreateUser:
    """
    Use case: Create a new user.

    UPDATED WITH TASK QUEUE:
    ─────────────────────────
    Now accepts an OPTIONAL TaskQueue dependency.
    After creating the user, it enqueues a welcome email
    as a background task.

    WHY OPTIONAL?
    The task_queue parameter defaults to None so that:
    1. Existing tests that don't care about emails still work
    2. If Redis is down, user creation still succeeds
    3. The email is a "fire-and-forget" side effect

    The use case depends on the abstract TaskQueue PORT,
    not on arq directly. This is hexagonal architecture in action.
    """

    def __init__(self, repo: UserRepository, task_queue: TaskQueue | None = None):
        self.repo = repo
        self.task_queue = task_queue

    async def execute(self, name: str, email: str):
        # ── Business Rule: No duplicate emails ──
        existing = await self.repo.find_by_email(email.strip().lower())
        if existing:
            raise ValueError(f"A user with email '{email}' already exists")

        # Entity-level validation (name length, email format) happens
        # automatically inside the User constructor via Pydantic validators
        user = User(name=name, email=email)
        created_user = await self.repo.create(user)

        # ── Background Task: Send welcome email ──
        if self.task_queue:
            await self.task_queue.enqueue(
                "send_welcome_email",
                email=created_user.email,
                name=created_user.name,
            )

        return created_user
