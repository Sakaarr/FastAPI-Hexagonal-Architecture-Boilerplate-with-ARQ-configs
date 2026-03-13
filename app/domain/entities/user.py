import re
from pydantic import BaseModel, field_validator
from typing import Optional


class User(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    password_hash: Optional[str] = None

    # ── Business Rule 1: Name must be at least 2 characters ──
    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Name must not exceed 100 characters")
        return v

    # ── Business Rule 2: Email must be a valid format ──
    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v):
        v = v.strip().lower()
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v

    def to_public_dict(self) -> dict:
        """
        Return user data WITHOUT the password hash.
        Always use this when sending user data in API responses.

        SECURITY RULE:
        ─────────────────
        Never expose password_hash to the client.
        This method excludes it from the response.
        """
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
        }
