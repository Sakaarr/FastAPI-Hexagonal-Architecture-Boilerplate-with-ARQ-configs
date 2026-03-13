from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.product import Product


class ProductRepository(ABC):

    @abstractmethod
    async def create(self, product: Product) -> Product:
        pass

    @abstractmethod
    async def get(self, product_id: str) -> Product | None:
        pass

    @abstractmethod
    async def list(self) -> List[Product]:
        pass

    @abstractmethod
    async def update(self, product_id: str, product: Product) -> Product:
        pass

    @abstractmethod
    async def delete(self, product_id: str) -> None:
        pass

    # ── New port method: find by name (needed for duplicate check) ──
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Product]:
        pass