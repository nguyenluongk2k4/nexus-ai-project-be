from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

@dataclass
class Mission:
    id: UUID
    name: str
    description: Optional[str]
    mission_type: str  # 'invite_friend', 'update_profile', 'purchase_plan', 'try_service'
    coin_reward: int
    is_repeatable: bool = False
    repeat_frequency: Optional[str] = None  # 'daily', 'weekly', 'monthly'
    max_per_period: Optional[int] = None
    requirements: Optional[Dict[str, Any]] = None
    is_active: bool = True
    icon: Optional[str] = None
    created_at: datetime = datetime.now()

@dataclass
class UserMission:
    id: UUID
    user_id: UUID
    mission_id: UUID
    status: str  # 'in_progress', 'completed'
    progress: Dict[str, Any]
    completed_at: Optional[datetime] = None
    coins_earned: int = 0
    created_at: datetime = datetime.now()
