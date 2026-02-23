from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from modules.referral.domain.entities import Referral


class ReferralRepositoryPort(ABC):

    @abstractmethod
    async def save(self, referral: Referral) -> Referral:
        pass

    @abstractmethod
    async def get_by_referee_id(self, user_id: UUID) -> Optional[Referral]:
        pass

    @abstractmethod
    async def get_referrals_by_referrer(self, user_id: UUID) -> List[Referral]:
        pass

    @abstractmethod
    async def get_referrer_by_code(self, code: str) -> Optional[UUID]:
        pass

    @abstractmethod
    async def is_code_exists(self, code: str) -> bool:
        pass

    @abstractmethod
    async def get_or_create_user_code(self, user_id: UUID) -> str:
        pass
