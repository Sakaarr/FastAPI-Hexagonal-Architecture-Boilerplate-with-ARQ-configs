from bson import ObjectId
from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.database.mongodb import db

product_collection = db["products"]

class MongoProductRepository(ProductRepository):

    async def create(self, product: Product):
        result = await product_collection.insert_one(product.dict(exclude={"id"}))
        product.id = str(result.inserted_id)
        return product

    
    async def get(self, product_id: str):
        doc = await product_collection.find_one({"_id": ObjectId(product_id)})
        if not doc:
            return None
        return Product(id=str(doc["_id"]), name=doc['name'], price=doc["price"], description=doc.get("description"))

    async def list(self):

        products = []

        async for doc in product_collection.find():

            products.append(
                Product(
                    id=str(doc["_id"]),
                    name=doc["name"],
                    price=doc["price"],
                    description=doc.get("description")
                )
            )

        return products

    async def update(self, product_id: str, product: Product):
        result = await product_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": product.dict(exclude={"id"})}
        )
        if result.modified_count == 0:
            return None
        return product
        
    async def delete(self, product_id: str):
        await product_collection.delete_one({"_id": ObjectId(product_id)})

    async def find_by_name(self, name: str):
        doc = await product_collection.find_one({"name": name})
        if not doc:
            return None
        return Product(
            id=str(doc["_id"]),
            name=doc["name"],
            price=doc["price"],
            description=doc.get("description")
        )
