# Auth Module - API Schemas

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class RegisterRequest(BaseModel):
    """Request for user registration"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    """Request for user login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response with JWT token"""
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    """Request to send OTP for password reset"""
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    """Request to verify the 6-digit OTP"""
    email: EmailStr
    otp: str

    model_config = ConfigDict(populate_by_name=True)


class ResetPasswordRequest(BaseModel):
    """Request to reset password after OTP verification"""
    email: EmailStr
    reset_token: str = Field(..., alias="resetToken")
    new_password: str = Field(..., alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(BaseModel):
    """Response with user info"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    balance: float = 0.0
    subscription_tier: Optional[str] = "free"
    subscription_expires_at: Optional[datetime] = None
    is_admin: bool = False
    role: str = "member"
    points: int = 0
    forum_rank: str = "Member"
    has_completed_tour: bool = False
    has_completed_dashboard_tour: bool = False
    has_completed_skilltree_tour: bool = False
    has_completed_master_skilltree_tour: bool = False
    streak: int = 0
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Response with token and user info"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
