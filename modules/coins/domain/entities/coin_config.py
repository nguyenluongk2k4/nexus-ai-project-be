from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime

@dataclass
class CoinConfig:
    id: UUID
    feature_key: str
    cost: int
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
