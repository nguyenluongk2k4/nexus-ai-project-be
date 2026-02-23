import string
import random
import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from modules.referral.domain.ports import ReferralRepositoryPort
from modules.referral.domain.entities import Referral
from modules.coins.infrastructure.models import ReferralModel  # Dùng ReferralModel từ Coins module
from modules.auth.infrastructure.models import UserModel

logger = logging.getLogger(__name__)


class SQLAlchemyReferralRepository(ReferralRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ReferralModel) -> Referral:
        return Referral(
            id=model.id,
            referrer_id=model.referrer_id,
            referee_id=model.referee_id,
            referral_code=model.referral_code,
            status=model.status,
            coins_awarded=model.coins_awarded,
            created_at=model.created_at,
            completed_at=model.completed_at
        )

    def _to_model(self, entity: Referral) -> ReferralModel:
        return ReferralModel(
            id=entity.id,
            referrer_id=entity.referrer_id,
            referee_id=entity.referee_id,
            referral_code=entity.referral_code,
            status=entity.status,
            coins_awarded=entity.coins_awarded,
            created_at=entity.created_at,
            completed_at=entity.completed_at
        )

    async def save(self, referral: Referral) -> Referral:
        model = self._to_model(referral)
        merged = await self.session.merge(model)
        await self.session.flush()
        return self._to_entity(merged)

    async def get_by_referee_id(self, user_id: UUID) -> Optional[Referral]:
        stmt = select(ReferralModel).where(ReferralModel.referee_id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_referrals_by_referrer(self, user_id: UUID) -> List[Referral]:
        stmt = select(ReferralModel).where(
            ReferralModel.referrer_id == user_id
        ).order_by(ReferralModel.created_at.desc())
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_referrer_by_code(self, code: str) -> Optional[UUID]:
        stmt = select(UserModel.id).where(UserModel.referral_code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_code_exists(self, code: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.referral_code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_or_create_user_code(self, user_id: UUID) -> str:
        """
        Lấy mã giới thiệu của user.
        - User mới: code được gen sẵn lúc đăng ký
        - User cũ (trước khi có tính năng): fallback Base62 gen tại đây
        """
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Người dùng không tồn tại")

        if user.referral_code:
            return user.referral_code

        # Fallback cho user cũ chưa có code (đã được backfill bởi SQL migration)
        # Trường hợp này chỉ xảy ra nếu SQL backfill chưa được chạy
        code = self._uuid_to_base62(user_id, length=8)
        user.referral_code = code
        try:
            await self.session.flush()
            logger.info(f"Fallback generated Base62 code {code} for old user {user_id}")
            return code
        except IntegrityError:
            await self.session.rollback()
            raise ValueError(f"Không thể tạo mã cho user {user_id}. Hãy chạy SQL backfill migration.")


    @staticmethod
    def _uuid_to_base62(user_id: UUID) -> str:
        """
        Generate referral code: UUID prefix (8 hex) + random Base62 (8 chars)
        Format: XXXXXXXX + YYYYYYYY = 16 chars total
        
        Example: 
        - UUID: 0859cc4d-f6b2-499b-a1c3-10aecfa0ac26
        - Prefix (hex): 0859cc4d (from UUID hex)
        - Suffix (random): Ab12Cd34 (random Base62)
        - Result: 0859cc4dAb12Cd34
        """
        import random
        import string
        
        # Extract first 8 chars from UUID hex (XXXXXXXX from XXXXXXXX-XXXX-...)
        uuid_hex = user_id.hex  # Remove dashes: convert to 32 hex chars
        hex_prefix = uuid_hex[:8]  # First 8 chars
        
        # Generate 8 random Base62 chars
        BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        random_suffix = ''.join(random.choices(BASE62, k=8))
        
        # Combine prefix + suffix
        return hex_prefix + random_suffix


