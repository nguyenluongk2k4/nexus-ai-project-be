import logging
from uuid import UUID
from modules.referral.domain.services.referral_service import ReferralService
from modules.referral.domain.ports import ReferralRepositoryPort

logger = logging.getLogger(__name__)


class ApplyReferralUseCase:
    def __init__(self, service: ReferralService, db_session):
        self.service = service
        self.session = db_session

    async def execute(self, referee_id: UUID, code: str) -> dict:
        code = code.strip().upper()
        if not code:
            return {"success": False, "message": "Mã giới thiệu không được để trống", "coins_awarded": 0}

        try:
            referral = await self.service.validate_and_apply_code(referee_id, code)

            # TODO: Tích hợp CoinService để cộng xu cho cả 2 bên
            coins_reward = 500
            referral.status = "completed"
            referral.coins_awarded = coins_reward * 2
            await self.service.repo.save(referral)
            await self.session.commit()

            return {
                "success": True,
                "message": f"Áp dụng thành công! Cả hai được tặng {coins_reward} xu.",
                "coins_awarded": coins_reward
            }
        except ValueError as e:
            await self.session.rollback()
            return {"success": False, "message": str(e), "coins_awarded": 0}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error applying referral code: {e}")
            return {"success": False, "message": "Đã xảy ra lỗi hệ thống", "coins_awarded": 0}


class GetReferralStatsUseCase:
    def __init__(self, repo: ReferralRepositoryPort):
        self.repo = repo

    async def execute(self, user_id: UUID) -> dict:
        import asyncio
        my_code, referrals, applied_referral = await asyncio.gather(
            self.repo.get_or_create_user_code(user_id),
            self.repo.get_referrals_by_referrer(user_id),
            self.repo.get_by_referee_id(user_id)
        )
        
        referred_by_code = applied_referral.referral_code if applied_referral else None

        return {
            "my_code": my_code,
            "total_invited": len(referrals),
            "total_earned": sum(r.coins_awarded for r in referrals if r.status == "completed"),
            "referred_by_code": referred_by_code,
            "history": [
                {
                    "referee_id": str(r.referee_id),
                    "status": r.status,
                    "date": r.created_at.isoformat()
                }
                for r in referrals
            ]
        }
