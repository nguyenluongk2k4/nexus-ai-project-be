from pydantic import BaseModel
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime

class CoinsBalanceResponse(BaseModel):
    current_coins: int
    lifetime_earned: int
    lifetime_spent: int

class ExchangeRequest(BaseModel):
    from_currency: str  # "balance" or "coins"
    amount: float

class TransactionResponse(BaseModel):
    id: UUID
    amount: int
    balance_after: int
    transaction_type: str
    service_type: Optional[str]
    description: Optional[str]
    created_at: datetime

class MissionResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    mission_type: str
    coin_reward: int
    is_repeatable: bool
    icon: Optional[str]
    requirements: dict = {}

class UserMissionResponse(BaseModel):
    mission_id: UUID
    status: str
    progress: dict
    completed_at: Optional[datetime]
    coins_earned: int

class ReferralStatsResponse(BaseModel):
    referral_code: str
    total_referrals: int
    total_earned: int
