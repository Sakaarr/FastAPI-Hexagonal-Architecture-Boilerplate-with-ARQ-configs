from app.domain.repositories.product_repository import ProductRepository


class GetProduct:

    def __init__(self, repo: ProductRepository):
        self.repo = repo

    async def execute(self, product_id: str):
        product = await self.repo.get(product_id)

        # ── Business Rule: Product must exist ──
        if not product:
            raise ValueError(f"Product with id '{product_id}' not found")

        return product
