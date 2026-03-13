from pydantic import BaseModel, field_validator
from typing import Optional


class Product(BaseModel):
    id: Optional[str] = None
    name: str
    price: float
    description: Optional[str] = None

    # ── Business Rule 1: Product name must be 2-200 characters ──
    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Product name must be at least 2 characters long")
        if len(v) > 200:
            raise ValueError("Product name must not exceed 200 characters")
        return v

    # ── Business Rule 2: Price must be positive ──
    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        if v > 1_000_000:
            raise ValueError("Price cannot exceed 1,000,000")
        return round(v, 2)  # Always store to 2 decimal places

    # ── Business Rule 3: Description length limit ──
    @field_validator("description")
    @classmethod
    def description_length_check(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 1000:
                raise ValueError("Description must not exceed 1000 characters")
            if len(v) == 0:
                return None  # Treat empty string as None
        return v
