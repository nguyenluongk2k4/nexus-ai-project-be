from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from shared.database.connection import get_db
from modules.auth.api.deps import get_current_user
from modules.auth.domain.entities import User

from modules.referral.domain.services.referral_service import ReferralService
from modules.referral.infrastructure.repository import SQLAlchemyReferralRepository
from modules.referral.usecases.referral_usecases import ApplyReferralUseCase, GetReferralStatsUseCase
from modules.referral.api.schemas import (
    ApplyReferralRequest,
    ApplyReferralResponse,
    ReferralStatsResponse,
    ReferralHistoryItemResponse,
)

router = APIRouter(prefix="/referral", tags=["Referral"])


def get_referral_repo(db: AsyncSession = Depends(get_db)) -> SQLAlchemyReferralRepository:
    return SQLAlchemyReferralRepository(db)


def get_referral_service(repo: SQLAlchemyReferralRepository = Depends(get_referral_repo)) -> ReferralService:
    return ReferralService(repo)


@router.post("/apply", response_model=ApplyReferralResponse)
async def apply_referral_code(
    payload: ApplyReferralRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: ReferralService = Depends(get_referral_service),
):
    """Nhập mã giới thiệu của người khác để nhận xu"""
    usecase = ApplyReferralUseCase(service, db)
    result = await usecase.execute(current_user.id, payload.code)
    return ApplyReferralResponse(**result)


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: SQLAlchemyReferralRepository = Depends(get_referral_repo),
):
    """Lấy mã giới thiệu + thống kê bạn bè đã mời"""
    usecase = GetReferralStatsUseCase(repo)
    result = await usecase.execute(current_user.id)
    await db.commit()
    return ReferralStatsResponse(
        my_code=result["my_code"],
        total_invited=result["total_invited"],
        total_earned=result["total_earned"],
        referred_by_code=result.get("referred_by_code"),
        history=[ReferralHistoryItemResponse(**h) for h in result["history"]],
    )


@router.get("/my-code")
async def get_my_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: SQLAlchemyReferralRepository = Depends(get_referral_repo),
):
    """Lấy nhanh mã giới thiệu cá nhân"""
    code = await repo.get_or_create_user_code(current_user.id)
    await db.commit()
    return {"code": code}
