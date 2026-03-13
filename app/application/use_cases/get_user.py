from app.domain.repositories.user_repository import UserRepository


class GetUser:

    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def execute(self, user_id: str):
        user = await self.repo.get(user_id)

        # ── Business Rule: User must exist ──
        if not user:
            raise ValueError(f"User with id '{user_id}' not found")

        return user
