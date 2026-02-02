from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from modules.coins.domain.entities.transaction import UserCoins, CoinTransaction

class CoinsRepositoryPort(ABC):
    @abstractmethod
    async def get_user_coins(self, user_id: UUID) -> Optional[UserCoins]:
        pass

    @abstractmethod
    async def update_user_coins(self, user_coins: UserCoins) -> UserCoins:
        pass

    @abstractmethod
    async def create_transaction(self, transaction: CoinTransaction) -> CoinTransaction:
        pass

    @abstractmethod
    async def get_transactions_by_user(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[CoinTransaction]:
        pass
