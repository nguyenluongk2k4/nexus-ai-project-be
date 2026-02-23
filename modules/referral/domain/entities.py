from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Referral:
    id: UUID = field(default_factory=uuid4)
    referrer_id: Optional[UUID] = None
    referee_id: Optional[UUID] = None
    referral_code: str = ""
    status: str = "pending"
    coins_awarded: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
