import re
from pydantic import BaseModel, field_validator
from typing import Optional


class User(BaseModel):
    id: Optional[str] = None
    name: str
    email: str

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
