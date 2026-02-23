# Auth Module - Domain Entities

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from .enums import ForumRank


@dataclass
class User:
    """User entity for authentication"""
    id: UUID = field(default_factory=uuid4)
    email: str = ""
    username: str = ""
    password_hash: str = ""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "member"
    points: int = 0
    balance: float = 0.0
    subscription_tier: Optional[str] = "free"
    subscription_expires_at: Optional[datetime] = None
    is_admin: bool = False
    is_active: bool = True
    google_id: Optional[str] = None
    referral_code: Optional[str] = None
    has_completed_tour: bool = False
    has_completed_dashboard_tour: bool = False
    has_completed_skilltree_tour: bool = False
    has_completed_master_skilltree_tour: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None

    @property
    def forum_rank(self) -> str:
        return ForumRank.from_points(self.points).value


@dataclass
class TokenPayload:
    """JWT token payload"""
    user_id: str
    email: str
    exp: datetime
