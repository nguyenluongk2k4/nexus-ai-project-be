from uuid import UUID, uuid4
from typing import Optional
from datetime import datetime
from modules.coins.domain.ports.coins_repository import CoinsRepositoryPort
from modules.coins.domain.services.coins_service import CoinsService

class ReferralService:
    def __init__(self, coins_service: CoinsService):
        self.coins_service = coins_service

    async def process_new_referral(self, referrer_id: UUID, referee_id: UUID, referral_code: str):
        # 1. Award coins to referrer (e.g., 50 coins)
        await self.coins_service.award_coins(
            user_id=referrer_id,
            amount=50, # Should come from config
            transaction_type='referral',
            reference_id=referee_id,
            description=f"Awarded for referring user {referee_id}"
        )
        
        # 2. Award welcome bonus to referee (e.g., 10 coins)
        await self.coins_service.award_coins(
            user_id=referee_id,
            amount=10, # Should come from config
            transaction_type='referral',
            reference_id=referrer_id,
            description=f"Welcome bonus for using referral code {referral_code}"
        )

    async def process_first_purchase(self, referrer_id: UUID, referee_id: UUID):
        # Additional bonus when referee buys a plan
        await self.coins_service.award_coins(
            user_id=referrer_id,
            amount=100, # Should come from config
            transaction_type='referral_bonus',
            reference_id=referee_id,
            description=f"Bonus for referee {referee_id} first purchase"
        )
