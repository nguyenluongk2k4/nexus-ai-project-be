from uuid import UUID
from typing import Dict, Any
from modules.coins.domain.services.mission_service import MissionService

class CompleteMissionUseCase:
    def __init__(self, mission_service: MissionService):
        self.mission_service = mission_service

    async def execute(self, user_id: UUID, mission_type: str, progress_data: Dict[str, Any]):
        await self.mission_service.update_progress(user_id, mission_type, progress_data)
