from app.domain.entities.product import Product

class UpdateProduct:

    def __init__(self, repo):
        self.repo = repo

    async def execute(self, product_id, name, price, description):
        product = Product(name=name, price=price, description=description)
        return await self.repo.update(product_id, product)
