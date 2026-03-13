from app.domain.entities.user import User

class UpdateUser:

    def __init__(self, repo):
        self.repo = repo

    async def execute(self, user_id, name, email):
        user = User(name=name, email=email)
        return await self.repo.update(user_id, user)
