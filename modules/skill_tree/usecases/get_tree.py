from modules.skill_tree.domain.ports import SkillTreePort
from uuid import UUID

class GetSessionSkillTreeUseCase:
    def __init__(self, repository: SkillTreePort):
        self.repository = repository

    async def execute(self, session_id: str, user_id: UUID) -> dict:
        # Future: We might want to look up session context to see if it overrides the tree.
        # For now, we simply fetch the active tree for the user.
        
        tree_data = await self.repository.get_user_tree(user_id)
        if not tree_data:
            return {}
            
        return tree_data
