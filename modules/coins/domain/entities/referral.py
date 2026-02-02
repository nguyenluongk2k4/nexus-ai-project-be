from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class Referral:
    id: UUID
    referrer_id: UUID
    referee_id: Optional[UUID]
    referral_code: str
    status: str  # 'pending', 'registered', 'completed', 'rewarded'
    coins_awarded: int = 0
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None
