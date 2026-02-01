# Subscription Module - API Routes
# Endpoints for subscription plans management

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from modules.auth.api.deps import get_current_user
from modules.auth.domain.entities import User
from shared.database.connection import get_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/subscription", tags=["Subscription"])


# ============================================================
# SCHEMAS
# ============================================================

class PlanFeature(BaseModel):
    text: str


class SubscriptionPlan(BaseModel):
    id: str
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: List[str]
    badge_color: str
    is_popular: bool


class UserSubscription(BaseModel):
    tier: str
    tier_name: str
    expires_at: Optional[datetime]
    is_active: bool


class PurchasePlanRequest(BaseModel):
    plan_id: str
    billing_cycle: str  # 'monthly' or 'yearly'


class PurchasePlanResponse(BaseModel):
    success: bool
    message: str
    new_tier: str
    expires_at: datetime
    amount_charged: float


# ============================================================
# ENDPOINTS
# ============================================================

@router.get(
    "/plans",
    response_model=List[SubscriptionPlan],
    summary="Lấy danh sách các gói đăng ký"
)
async def get_subscription_plans(
    session: AsyncSession = Depends(get_db)
):
    """Get all available subscription plans"""
    
    result = await session.execute(
        text("""
            SELECT id, name, description, price_monthly, price_yearly, 
                   features, badge_color, is_popular
            FROM subscription_plans
            WHERE is_active = TRUE
            ORDER BY display_order ASC
        """)
    )
    
    plans = []
    for row in result.fetchall():
        features = row.features if isinstance(row.features, list) else []
        plans.append(SubscriptionPlan(
            id=row.id,
            name=row.name,
            description=row.description or "",
            price_monthly=float(row.price_monthly),
            price_yearly=float(row.price_yearly),
            features=features,
            badge_color=row.badge_color or "#8B5CF6",
            is_popular=row.is_popular or False
        ))
    
    return plans


@router.get(
    "/current",
    response_model=UserSubscription,
    summary="Lấy thông tin gói đăng ký hiện tại"
)
async def get_current_subscription(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get current user's subscription info"""
    
    result = await session.execute(
        text("""
            SELECT u.subscription_tier, u.subscription_expires_at, sp.name
            FROM users u
            LEFT JOIN subscription_plans sp ON u.subscription_tier = sp.id
            WHERE u.id = :user_id
        """),
        {"user_id": str(user.id)}
    )
    row = result.fetchone()
    
    tier = row.subscription_tier or "free" if row else "free"
    tier_name = row.name or "Free" if row else "Free"
    expires_at = row.subscription_expires_at if row else None
    
    # Check if expired
    is_active = True
    if tier != "free" and expires_at:
        if expires_at < datetime.now():
            is_active = False
            # Auto-downgrade to free
            await session.execute(
                text("""
                    UPDATE users 
                    SET subscription_tier = 'free', subscription_expires_at = NULL
                    WHERE id = :user_id
                """),
                {"user_id": str(user.id)}
            )
            await session.commit()
            tier = "free"
            tier_name = "Free"
    
    return UserSubscription(
        tier=tier,
        tier_name=tier_name,
        expires_at=expires_at if is_active else None,
        is_active=is_active
    )


@router.post(
    "/purchase",
    response_model=PurchasePlanResponse,
    summary="Mua gói đăng ký"
)
async def purchase_plan(
    data: PurchasePlanRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Purchase a subscription plan using account balance"""
    
    # Validate billing cycle
    if data.billing_cycle not in ['monthly', 'yearly']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chu kỳ thanh toán không hợp lệ"
        )
    
    # Get plan details
    plan_result = await session.execute(
        text("""
            SELECT id, name, price_monthly, price_yearly
            FROM subscription_plans
            WHERE id = :plan_id AND is_active = TRUE
        """),
        {"plan_id": data.plan_id}
    )
    plan = plan_result.fetchone()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gói đăng ký không tồn tại"
        )
    
    # Check if user already has this plan
    user_result = await session.execute(
        text("SELECT subscription_tier, COALESCE(balance, 0) as balance FROM users WHERE id = :user_id"),
        {"user_id": str(user.id)}
    )
    user_data = user_result.fetchone()
    
    if user_data.subscription_tier == data.plan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã đang sử dụng gói này"
        )
    
    # Calculate price and expiry
    if data.billing_cycle == 'monthly':
        price = float(plan.price_monthly)
        expires_at = datetime.now() + timedelta(days=30)
    else:
        price = float(plan.price_yearly)
        expires_at = datetime.now() + timedelta(days=365)
    
    # Check balance
    current_balance = float(user_data.balance)
    if current_balance < price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số dư không đủ. Cần {price:,.0f}đ, hiện có {current_balance:,.0f}đ"
        )
    
    # Deduct balance and update subscription
    new_balance = current_balance - price
    
    await session.execute(
        text("""
            UPDATE users
            SET balance = :new_balance,
                subscription_tier = :tier,
                subscription_expires_at = :expires_at
            WHERE id = :user_id
        """),
        {
            "new_balance": new_balance,
            "tier": data.plan_id,
            "expires_at": expires_at,
            "user_id": str(user.id)
        }
    )
    
    # Record transaction
    await session.execute(
        text("""
            INSERT INTO subscription_transactions 
            (user_id, plan_id, billing_cycle, amount, starts_at, expires_at, status)
            VALUES (:user_id, :plan_id, :cycle, :amount, NOW(), :expires_at, 'active')
        """),
        {
            "user_id": str(user.id),
            "plan_id": data.plan_id,
            "cycle": data.billing_cycle,
            "amount": price,
            "expires_at": expires_at
        }
    )
    
    # Also record as a 'purchase' type transaction in main transactions table
    await session.execute(
        text("""
            INSERT INTO transactions (user_id, type, amount, balance_before, balance_after, status, note)
            VALUES (:user_id, 'purchase', :amount, :before, :after, 'completed', :note)
        """),
        {
            "user_id": str(user.id),
            "amount": price,
            "before": current_balance,
            "after": new_balance,
            "note": f"Mua gói {plan.name} ({data.billing_cycle})"
        }
    )
    
    await session.commit()
    
    # Coins Integration: Award 100 coins bonus for purchase
    try:
        from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository
        from modules.coins.domain.services.coins_service import CoinsService
        from modules.coins.domain.services.mission_service import MissionService
        
        coins_repo = SQLAlchemyCoinsRepository(session)
        coins_service = CoinsService(coins_repo)
        mission_repo = SQLAlchemyMissionRepository(session)
        mission_service = MissionService(mission_repo, coins_service)
        
        # 1. Direct Award
        await coins_service.award_coins(
            user_id=user.id,
            amount=100,
            transaction_type='purchase_bonus',
            description=f"Bonus for purchasing {plan.name}"
        )
        
        # 2. Trigger Mission
        await mission_service.update_progress(
            user_id=user.id,
            mission_type='purchase_plan',
            progress_data={'plan_id': data.plan_id}
        )
    except Exception as e:
        print(f"Failed to award bonus coins: {e}")

    return PurchasePlanResponse(
        success=True,
        message=f"Đã nâng cấp lên gói {plan.name} thành công!",
        new_tier=data.plan_id,
        expires_at=expires_at,
        amount_charged=price
    )
