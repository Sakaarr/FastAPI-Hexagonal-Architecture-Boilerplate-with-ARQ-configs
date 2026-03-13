from bson import ObjectId
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.mongodb import user_collection


class MongoUserRepository(UserRepository):

    async def create(self, user: User):

        result = await user_collection.insert_one(user.dict(exclude={"id"}))

        user.id = str(result.inserted_id)

        return user


    async def get(self, user_id: str):

        doc = await user_collection.find_one({"_id": ObjectId(user_id)})

        if not doc:
            return None

        return User(
            id=str(doc["_id"]),
            name=doc["name"],
            email=doc["email"]
        )


    async def list(self):

        users = []

        async for doc in user_collection.find():

            users.append(
                User(
                    id=str(doc["_id"]),
                    name=doc["name"],
                    email=doc["email"]
                )
            )

        return users


    async def update(self, user_id, user):

        await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user.dict(exclude={"id"})}
        )

        return await self.get(user_id)


    async def delete(self, user_id):

        await user_collection.delete_one({"_id": ObjectId(user_id)})

    async def find_by_email(self, email: str):

        doc = await user_collection.find_one({"email": email})

        if not doc:
            return None

        return User(
            id=str(doc["_id"]),
            name=doc["name"],
            email=doc["email"],
            password_hash=doc.get("password_hash"),
        )
