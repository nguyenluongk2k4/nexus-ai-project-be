from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from modules.coins.domain.entities.mission import Mission, UserMission

class MissionRepositoryPort(ABC):
    @abstractmethod
    async def get_mission(self, mission_id: UUID) -> Optional[Mission]:
        pass

    @abstractmethod
    async def get_active_missions(self) -> List[Mission]:
        pass

    @abstractmethod
    async def get_user_mission(self, user_id: UUID, mission_id: UUID) -> Optional[UserMission]:
        pass

    @abstractmethod
    async def get_user_missions(self, user_id: UUID) -> List[UserMission]:
        pass

    @abstractmethod
    async def update_user_mission(self, user_mission: UserMission) -> UserMission:
        pass

    @abstractmethod
    async def create_user_mission(self, user_mission: UserMission) -> UserMission:
        pass
