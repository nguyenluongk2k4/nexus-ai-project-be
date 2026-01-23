from modules.skill_tree.domain.ports import SkillTreePort
from uuid import UUID
from typing import Optional

class GetNodeResourcesUseCase:
    def __init__(self, repository: SkillTreePort):
        self.repository = repository


    async def execute(self, node_id: str, user_id: UUID) -> list:
        # Check if node_id is valid UUID
        try:
            node_uuid = UUID(node_id)
        except ValueError:
            return []
            
        repo = self.repository
        
        # 1. Try fetching for this specific node ID (User node or Template node)
        resources_map = await repo.get_resources_for_nodes([node_id], user_id)
        
        if resources_map.get(node_id):
            return resources_map.get(node_id)
        
        # 2. Fallback: If it's a saved UserNode, it might have a unique UserNode ID
        # but link to a TemplateNode via original_node_id
        from shared.database.connection import get_db_context
        from modules.skill_tree.infrastructure.models import UserSkillNodeModel
        from sqlalchemy import select
        
        async with get_db_context() as session:
            stmt = select(UserSkillNodeModel.original_node_id).where(UserSkillNodeModel.id == node_uuid)
            res = await session.execute(stmt)
            db_orig_id = res.scalar_one_or_none()
            
            if db_orig_id:
                # Fetch resources for the mapped template node
                resources_map = await repo.get_resources_for_nodes([str(db_orig_id)], user_id)
                return resources_map.get(str(db_orig_id), [])
                    
        return []
