# User Module - API Schemas

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class CreateUserRequest(BaseModel):
    """Request for creating a new user"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True


class UpdateUserRequest(BaseModel):
    """Request for updating user - only admin fields"""
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserResponse(BaseModel):
    """Response with user info"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    balance: float
    subscription_tier: Optional[str]
    subscription_expires_at: Optional[datetime] = None
    is_admin: bool
    role: str
    points: int
    forum_rank: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """Response with list of users and pagination"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
