"""
╔══════════════════════════════════════════════════════════════╗
║  USE CASE: Login User                                        ║
║                                                              ║
║  Authenticates a user with email + password, returns a JWT.  ║
║  The use case doesn't know about HTTP — it just returns      ║
║  the token string. The router decides how to send it.        ║
╚══════════════════════════════════════════════════════════════╝
"""

from app.domain.repositories.user_repository import UserRepository
from app.domain.password_hasher import PasswordHasher
from app.infrastructure.security.jwt_handler import create_access_token


class LoginUser:
    """
    Use case: Authenticate a user and return a JWT token.

    FLOW:
    ──────
    1. Look up user by email
    2. Verify password against stored hash
    3. Generate JWT token with user_id as subject
    4. Return token + user info

    Dependencies:
    - repo: UserRepository — find user by email
    - hasher: PasswordHasher — verify password
    """

    def __init__(self, repo: UserRepository, hasher: PasswordHasher):
        self.repo = repo
        self.hasher = hasher

    async def execute(self, email: str, password: str) -> dict:
        # ── Step 1: Find user by email ──
        user = await self.repo.find_by_email(email.strip().lower())
        if not user:
            # SECURITY: Don't reveal whether email exists
            raise ValueError("Invalid email or password")

        # ── Step 2: Verify password ──
        if not user.password_hash:
            raise ValueError("Invalid email or password")

        if not self.hasher.verify(password, user.password_hash):
            raise ValueError("Invalid email or password")

        # ── Step 3: Generate JWT ──
        access_token = create_access_token(data={"sub": user.id})

        # ── Step 4: Return token + user info ──
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.to_public_dict(),
        }
