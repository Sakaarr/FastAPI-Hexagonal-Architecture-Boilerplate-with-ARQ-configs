from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository


class CreateProduct:

    def __init__(self, repo: ProductRepository):
        self.repo = repo

    async def execute(self, name: str, price: float, description: str = None):
        # ── Business Rule: No duplicate product names ──
        existing = await self.repo.find_by_name(name.strip())
        if existing:
            raise ValueError(f"A product with name '{name}' already exists")

        # Entity-level validation (name length, price positive, description)
        # happens automatically inside the Product constructor
        product = Product(name=name, price=price, description=description)
        return await self.repo.create(product)