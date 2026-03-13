"""
╔══════════════════════════════════════════════════════════════╗
║  DOMAIN PORT: Password Hasher Interface                      ║
║                                                              ║
║  An abstract contract for hashing and verifying passwords.   ║
║  The use case layer depends on this port — it never knows    ║
║  if bcrypt, argon2, or a fake hasher is being used.          ║
╚══════════════════════════════════════════════════════════════╝
"""

from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """
    Abstract port for password hashing.

    WHY THIS EXISTS:
    ─────────────────
    The RegisterUser use case needs to hash passwords, but it
    shouldn't be coupled to bcrypt or any specific algorithm.

    - In production: BcryptPasswordHasher (uses bcrypt)
    - In tests: FakePasswordHasher (plaintext for speed)
    - Could also be: Argon2PasswordHasher, ScryptPasswordHasher
    """

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plaintext password. Returns the hash string."""
        pass

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against its hash. Returns True if match."""
        pass
