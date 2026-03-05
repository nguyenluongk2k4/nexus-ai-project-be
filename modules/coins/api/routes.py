from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from modules.auth.api.deps import get_current_user_id
from shared.database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.services.mission_service import MissionService
from modules.coins.api.schemas import (
    CoinsBalanceResponse, 
    TransactionResponse, 
    MissionResponse, 
    UserMissionResponse,
    ExchangeRequest
)

router = APIRouter(prefix="/coins", tags=["Coins"])

from modules.coins.providers import get_coins_service, get_mission_service

@router.get("/balance", response_model=CoinsBalanceResponse)
async def get_balance(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    repo = SQLAlchemyCoinsRepository(db)
    user_coins = await repo.get_user_coins(user_id)
    if not user_coins:
        return CoinsBalanceResponse(current_coins=0, lifetime_earned=0, lifetime_spent=0)
    return CoinsBalanceResponse(
        current_coins=user_coins.current_coins,
        lifetime_earned=user_coins.lifetime_earned,
        lifetime_spent=user_coins.lifetime_spent
    )

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    user_id: UUID = Depends(get_current_user_id),
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    repo = SQLAlchemyCoinsRepository(db)
    transactions = await repo.get_transactions_by_user(user_id, limit, offset)
    return [TransactionResponse(
        id=t.id,
        amount=t.amount,
        balance_after=t.balance_after,
        transaction_type=t.transaction_type,
        service_type=t.service_type,
        description=t.description,
        created_at=t.created_at
    ) for t in transactions]

@router.get("/missions", response_model=List[MissionResponse])
async def get_missions(
    db: AsyncSession = Depends(get_db)
):
    repo = SQLAlchemyMissionRepository(db)
    missions = await repo.get_active_missions()
    return [MissionResponse(
        id=m.id,
        name=m.name,
        description=m.description,
        mission_type=m.mission_type,
        coin_reward=m.coin_reward,
        is_repeatable=m.is_repeatable,
        icon=m.icon,
        requirements=m.requirements or {}
    ) for m in missions]

@router.get("/missions/my-progress", response_model=List[UserMissionResponse])
async def get_my_missions(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    repo = SQLAlchemyMissionRepository(db)
    user_missions = await repo.get_user_missions(user_id)
    return [UserMissionResponse(
        mission_id=m.mission_id,
        status=m.status,
        progress=m.progress,
        completed_at=m.completed_at,
        coins_earned=m.coins_earned
    ) for m in user_missions]

@router.get("/referrals/my-code", response_model=dict)
async def get_referral_code(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # Fetch user from db to get their referral code
    from modules.auth.infrastructure.models import UserModel
    from sqlalchemy import select
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"referral_code": user.referral_code}

@router.get("/referrals/stats", response_model=dict)
async def get_referral_stats(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # This is a simplified implementation
    # In a real app, you'd count referrals from the referrals table
    return {
        "total_referrals": 0,
        "total_earned": 0
    }
@router.post("/missions/{mission_id}/claim", response_model=UserMissionResponse)
async def claim_mission_reward(
    mission_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    service = get_mission_service(db)
    try:
        user_mission = await service.claim_reward(user_id, mission_id)
        return UserMissionResponse(
            mission_id=user_mission.mission_id,
            status=user_mission.status,
            progress=user_mission.progress,
            completed_at=user_mission.completed_at,
            coins_earned=user_mission.coins_earned
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/exchange", response_model=dict)
async def exchange_currency(
    request: ExchangeRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Exchange balance to coins. 10,000 VND = 50 Coins (200 VND = 1 Coin)."""
    from modules.auth.infrastructure.models import UserModel
    from sqlalchemy import select
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
        
    service = get_coins_service(db)
    
    # Needs to lock user record to prevent race conditions during transaction
    result = await db.execute(select(UserModel).where(UserModel.id == user_id).with_for_update())
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if request.from_currency == "balance":
        if user.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
            
        coins_to_add = int(request.amount / 200)
        
        # Deduct balance
        user.balance = float(user.balance) - float(request.amount)
        
        # Add coins
        await service.award_coins(
            user_id=user_id,
            amount=coins_to_add,
            transaction_type="exchange",
            service_type="balance_to_coins",
            description=f"Exchange {int(request.amount)}đ to {coins_to_add} coins"
        )
        
        await db.commit()
        return {"status": "success", "message": f"Successfully exchanged {int(request.amount)}đ for {coins_to_add} coins", "new_balance": user.balance}
        
    elif request.from_currency == "coins":
        # Ensure user has enough coins
        current_coins = await service.get_balance(user_id)
        if current_coins < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient coins")
            
        # 1 coin = 200 VND
        money_to_add = int(request.amount * 200)
        
        # Deduct coins
        await service.spend_coins(
            user_id=user_id,
            amount=int(request.amount),
            service_type="coins_to_balance",
            description=f"Exchange {int(request.amount)} coins to {money_to_add}đ"
        )
        
        # Add to local balance
        user.balance = float(user.balance) + float(money_to_add)
        
        await db.commit()
        return {"status": "success", "message": f"Successfully exchanged {int(request.amount)} coins for {money_to_add}đ", "new_balance": user.balance}
        
    else:
        raise HTTPException(status_code=400, detail="Invalid from_currency, must be 'balance' or 'coins'")
