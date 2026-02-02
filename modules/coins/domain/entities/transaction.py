from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class CoinTransaction:
    id: UUID
    user_id: UUID
    amount: int
    balance_after: int
    transaction_type: str  # 'subscription', 'mission', 'referral', 'service', 'admin'
    service_type: Optional[str] = None
    reference_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: datetime = datetime.now()

@dataclass
class UserCoins:
    user_id: UUID
    current_coins: int
    lifetime_earned: int
    lifetime_spent: int
    last_refresh_date: Optional[datetime] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
