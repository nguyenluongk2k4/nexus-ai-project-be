from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from modules.coins.domain.entities.coin_config import CoinConfig

class CoinConfigRepositoryPort(ABC):
    @abstractmethod
    async def get_config(self, feature_key: str) -> Optional[CoinConfig]:
        pass
    
    @abstractmethod
    async def update_config(self, config: CoinConfig) -> CoinConfig:
        pass
