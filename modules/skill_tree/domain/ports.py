from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class SkillTreePort(ABC):
    @abstractmethod
    async def get_resources_for_nodes(self, node_ids: List[str], user_id: UUID) -> dict:
        pass
    
    @abstractmethod
    async def update_resource_progress(self, user_id: UUID, resource_id: str, status: str, progress_percent: int) -> any:
        pass

    @abstractmethod
    async def get_user_tree(self, user_id: UUID) -> Optional[dict]:
        pass
