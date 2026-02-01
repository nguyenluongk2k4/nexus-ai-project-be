from uuid import UUID
from modules.coins.domain.services.coins_service import CoinsService

class GetBalanceUseCase:
    def __init__(self, coins_service: CoinsService):
        self.coins_service = coins_service

    async def execute(self, user_id: UUID) -> int:
        return await self.coins_service.get_balance(user_id)
