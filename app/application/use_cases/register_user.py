"""
╔══════════════════════════════════════════════════════════════╗
║  USE CASE: Register User                                     ║
║                                                              ║
║  Handles user registration with password hashing.            ║
║  This is separate from CreateUser because registration       ║
║  involves password handling — a distinct business process.   ║
╚══════════════════════════════════════════════════════════════╝
"""

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.password_hasher import PasswordHasher
from app.domain.task_queue import TaskQueue


class RegisterUser:
    """
    Use case: Register a new user with a password.

    DIFFERS FROM CreateUser:
    ─────────────────────────
    - CreateUser: admin-facing, no password required
    - RegisterUser: user-facing, requires password + hashing

    Dependencies (all abstract ports):
    - repo: UserRepository — save/query users
    - hasher: PasswordHasher — hash passwords (bcrypt in prod)
    - task_queue: TaskQueue — send welcome email (optional)
    """

    def __init__(
        self,
        repo: UserRepository,
        hasher: PasswordHasher,
        task_queue: TaskQueue | None = None,
    ):
        self.repo = repo
        self.hasher = hasher
        self.task_queue = task_queue

    async def execute(self, name: str, email: str, password: str) -> User:
        # ── Business Rule: Password strength ──
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # ── Business Rule: No duplicate emails ──
        existing = await self.repo.find_by_email(email.strip().lower())
        if existing:
            raise ValueError(f"A user with email '{email}' already exists")

        # ── Hash the password ──
        # The hasher is injected — we don't know if it's bcrypt or fake
        password_hash = self.hasher.hash(password)

        # ── Create user entity with hashed password ──
        user = User(name=name, email=email, password_hash=password_hash)
        created_user = await self.repo.create(user)

        # ── Background Task: Send welcome email ──
        if self.task_queue:
            await self.task_queue.enqueue(
                "send_welcome_email",
                email=created_user.email,
                name=created_user.name,
            )

        return created_user
