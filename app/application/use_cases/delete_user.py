class DeleteUser:

    def __init__(self, repo):
        self.repo = repo

    async def execute(self, user_id):
        await self.repo.delete(user_id)
