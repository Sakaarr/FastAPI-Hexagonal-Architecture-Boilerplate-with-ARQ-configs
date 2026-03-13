"""
In-Memory Fakes for Testing
============================
These implement the same abstract ports as the production adapters,
but store everything in Python data structures. This lets you test
all business logic without a running database or Redis.
"""

import uuid
from typing import Any, List, Optional

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository

from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository

from app.domain.task_queue import TaskQueue


class FakeTaskQueue(TaskQueue):
    """
    In-memory task queue for testing — no Redis needed.

    Instead of enqueuing to Redis, it stores tasks in a list.
    Tests can then inspect self.enqueued_tasks to verify that
    the correct tasks were triggered with the correct arguments.
    """

    def __init__(self):
        self.enqueued_tasks: list[dict] = []

    async def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str | None:
        job_id = str(uuid.uuid4())
        self.enqueued_tasks.append({
            "job_id": job_id,
            "task_name": task_name,
            "args": args,
            "kwargs": kwargs,
        })
        return job_id


class FakeUserRepository(UserRepository):
    """In-memory user repository for testing — no database needed."""

    def __init__(self):
        self._storage: dict[str, User] = {}

    async def create(self, user: User) -> User:
        user.id = str(uuid.uuid4())
        self._storage[user.id] = user
        return user

    async def get(self, user_id: str) -> User | None:
        return self._storage.get(user_id)

    async def list(self) -> List[User]:
        return list(self._storage.values())

    async def update(self, user_id: str, user: User) -> User:
        if user_id not in self._storage:
            return None
        user.id = user_id
        self._storage[user_id] = user
        return user

    async def delete(self, user_id: str) -> None:
        self._storage.pop(user_id, None)

    async def find_by_email(self, email: str) -> Optional[User]:
        for user in self._storage.values():
            if user.email == email:
                return user
        return None


class FakeProductRepository(ProductRepository):
    """In-memory product repository for testing — no database needed."""

    def __init__(self):
        self._storage: dict[str, Product] = {}

    async def create(self, product: Product) -> Product:
        product.id = str(uuid.uuid4())
        self._storage[product.id] = product
        return product

    async def get(self, product_id: str) -> Product | None:
        return self._storage.get(product_id)

    async def list(self) -> List[Product]:
        return list(self._storage.values())

    async def update(self, product_id: str, product: Product) -> Product:
        if product_id not in self._storage:
            return None
        product.id = product_id
        self._storage[product_id] = product
        return product

    async def delete(self, product_id: str) -> None:
        self._storage.pop(product_id, None)

    async def find_by_name(self, name: str) -> Optional[Product]:
        for product in self._storage.values():
            if product.name == name:
                return product
        return None
