# Auth Module - Database Models

from datetime import datetime
from typing import Optional
from uuid import uuid4
import uuid as uuid_module

from sqlalchemy import String, Boolean, DateTime, Numeric, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.connection import Base


class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Allow password to be nullable for Google OAuth users
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    balance: Mapped[float] = mapped_column(Numeric, default=0.0)
    subscription_tier: Mapped[Optional[str]] = mapped_column(String(50), default="free")
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(Text, default="member")
    points: Mapped[int] = mapped_column(BigInteger, default=0)
    has_completed_tour: Mapped[bool] = mapped_column(Boolean, default=False)
    has_completed_dashboard_tour: Mapped[bool] = mapped_column(Boolean, default=False)
    has_completed_skilltree_tour: Mapped[bool] = mapped_column(Boolean, default=False)
    has_completed_master_skilltree_tour: Mapped[bool] = mapped_column(Boolean, default=False)
    streak: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
