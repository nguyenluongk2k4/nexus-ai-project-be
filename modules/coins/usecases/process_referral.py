from uuid import UUID
from modules.coins.domain.services.referral_service import ReferralService

class ProcessReferralUseCase:
    def __init__(self, referral_service: ReferralService):
        self.referral_service = referral_service

    async def execute(self, referrer_id: UUID, referee_id: UUID, referral_code: str):
        await self.referral_service.process_new_referral(referrer_id, referee_id, referral_code)
