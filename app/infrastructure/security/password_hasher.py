"""
╔══════════════════════════════════════════════════════════════╗
║  INFRASTRUCTURE: Bcrypt Password Hasher                      ║
║                                                              ║
║  Production implementation of the PasswordHasher port        ║
║  using the passlib library with bcrypt.                      ║
║                                                              ║
║  WHY passlib + bcrypt?                                       ║
║  - bcrypt is the industry standard for password hashing      ║
║  - Automatically handles salt generation                     ║
║  - Configurable cost factor (rounds) for future-proofing     ║
║  - passlib provides a clean API on top of bcrypt             ║
╚══════════════════════════════════════════════════════════════╝
"""

from passlib.context import CryptContext
from app.domain.password_hasher import PasswordHasher


# ── Configure bcrypt ──
# schemes=["bcrypt"] → uses bcrypt algorithm
# deprecated="auto" → auto-rehash if old algorithm detected
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher(PasswordHasher):
    """
    Production password hasher using bcrypt via passlib.

    LEARNING POINT — Why bcrypt?
    ──────────────────────────────
    bcrypt is designed to be SLOW on purpose. This makes
    brute-force attacks expensive. Each hash includes:
    - A random salt (prevents rainbow table attacks)
    - A cost factor (can increase over time as CPUs get faster)

    A typical bcrypt hash looks like:
    $2b$12$LJ3m4ys...(60 chars total)
     ↑   ↑
     │   └─ cost factor (12 rounds = 2^12 iterations)
     └─ bcrypt identifier
    """

    def hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return pwd_context.verify(password, password_hash)
