from modules.skill_tree.domain.ports import SkillTreePort
from uuid import UUID

class UpdateResourceProgressUseCase:
    def __init__(self, repository: SkillTreePort):
        self.repository = repository

    async def execute(self, resource_id: str, user_id: UUID, status: str, progress_percent: int = 0) -> dict:
        result = await self.repository.update_resource_progress(user_id, resource_id, status, progress_percent)
        return {"status": "success", "data": result}
