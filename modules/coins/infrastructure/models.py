# Coins Module - SQLAlchemy Models

from datetime import datetime, date
from typing import Optional
from uuid import uuid4
import uuid as uuid_module

from sqlalchemy import String, Integer, Boolean, DateTime, Date, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.connection import Base


class UserCoinsModel(Base):
    """User coins balance"""
    __tablename__ = "user_coins"
    
    user_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', ondelete='CASCADE'),
        primary_key=True
    )
    current_coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lifetime_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_refresh_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class CoinTransactionModel(Base):
    """Coin transaction log"""
    __tablename__ = "coin_transactions"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    service_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class MissionModel(Base):
    """Available missions"""
    __tablename__ = "missions"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission_type: Mapped[str] = mapped_column(String(50), nullable=False)
    coin_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    is_repeatable: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat_frequency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    max_per_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requirements: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class UserMissionModel(Base):
    """User mission progress"""
    __tablename__ = "user_missions"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    mission_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('missions.id', ondelete='CASCADE'),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default='in_progress')
    progress: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ReferralModel(Base):
    """Referral tracking"""
    __tablename__ = "referrals"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    referrer_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    referee_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    referral_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CoinConfigModel(Base):
    """Coin feature cost configuration"""
    __tablename__ = "coin_configs"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feature_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
