import random
import string
import logging
from uuid import UUID
from modules.referral.domain.ports import ReferralRepositoryPort
from modules.referral.domain.entities import Referral

logger = logging.getLogger(__name__)


class ReferralService:
    def __init__(self, referral_repo: ReferralRepositoryPort):
        self.repo = referral_repo

    def _generate_random_string(self, length: int = 8) -> str:
        """Sinh chuỗi ngẫu nhiên (A-Z, 0-9)"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))

    async def get_or_create_code(self, user_id: UUID) -> str:
        """Lazy generation entry point"""
        return await self.repo.get_or_create_user_code(user_id)

    async def validate_and_apply_code(self, referee_id: UUID, code: str) -> Referral:
        """
        Validate và áp dụng mã giới thiệu:
        1. User không được nhập mã của chính mình.
        2. User chỉ được nhập mã 1 lần duy nhất.
        3. Mã phải tồn tại.
        """
        existing = await self.repo.get_by_referee_id(referee_id)
        if existing:
            raise ValueError("Bạn đã sử dụng một mã giới thiệu rồi.")

        referrer_id = await self.repo.get_referrer_by_code(code)
        if not referrer_id:
            raise ValueError("Mã giới thiệu không hợp lệ hoặc không tồn tại.")

        if referrer_id == referee_id:
            raise ValueError("Bạn không thể tự nhập mã giới thiệu của chính mình.")

        new_referral = Referral(
            referrer_id=referrer_id,
            referee_id=referee_id,
            referral_code=code,
            status="pending"
        )
        return await self.repo.save(new_referral)
