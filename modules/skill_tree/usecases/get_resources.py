from modules.skill_tree.domain.ports import SkillTreePort
from uuid import UUID

class GetNodeResourcesUseCase:
    def __init__(self, repository: SkillTreePort):
        self.repository = repository


    async def execute(self, node_id: str, user_id: UUID) -> dict:
        # Check if node_id is valid UUID
        try:
            UUID(node_id)
        except ValueError:
            return {}  # Return empty if not a valid UUID (e.g. placeholder node)
            
        resources_map = await self.repository.get_resources_for_nodes([node_id], user_id)
        return resources_map.get(node_id, [])
