# Auth Module - Domain Entities

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class User:
    """User entity for authentication"""
    id: UUID = field(default_factory=uuid4)
    email: str = ""
    username: str = ""
    password_hash: str = ""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None


@dataclass
class TokenPayload:
    """JWT token payload"""
    user_id: str
    email: str
    exp: datetime
