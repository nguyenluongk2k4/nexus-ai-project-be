from uuid import UUID
from typing import Optional
from modules.coins.domain.services.coins_service import CoinsService

class SpendCoinsUseCase:
    def __init__(self, coins_service: CoinsService):
        self.coins_service = coins_service

    async def execute(
        self, 
        user_id: UUID, 
        amount: int, 
        service_type: str,
        description: Optional[str] = None
    ) -> int:
        return await self.coins_service.spend_coins(
            user_id=user_id,
            amount=amount,
            service_type=service_type,
            description=description
        )
