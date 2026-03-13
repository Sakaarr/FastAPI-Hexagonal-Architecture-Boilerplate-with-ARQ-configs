from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.user import User


class UserRepository(ABC):

    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def get(self, user_id: str) -> User | None:
        pass

    @abstractmethod
    async def list(self) -> List[User]:
        pass

    @abstractmethod
    async def update(self, user_id: str, user: User) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        pass

    # ── New port method: find by email (needed for duplicate check) ──
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        pass
