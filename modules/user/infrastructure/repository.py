# User Module - Repository Implementation

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, func, or_

from modules.auth.domain.entities import User
from modules.user.domain.ports import UserRepositoryPort
from modules.auth.infrastructure.models import UserModel
from shared.database.connection import async_session_maker


def _to_uuid(value) -> UUID:
    """Safely convert value to UUID"""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class UserRepositoryImpl(UserRepositoryPort):
    """SQLAlchemy implementation of UserRepositoryPort"""
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._to_entity(model)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.email == email)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._to_entity(model)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.username == username)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._to_entity(model)
    
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        subscription_tier: Optional[str] = None
    ) -> tuple[List[User], int]:
        """Get all users with pagination and optional filters"""
        async with async_session_maker() as db:
            # Base query
            query = select(UserModel)
            
            # Apply search filter if provided
            if search:
                search_filter = or_(
                    UserModel.email.ilike(f"%{search}%"),
                    UserModel.username.ilike(f"%{search}%"),
                    UserModel.full_name.ilike(f"%{search}%")
                )
                query = query.where(search_filter)
            
            # Apply status filter
            if is_active is not None:
                query = query.where(UserModel.is_active == is_active)
            
            # Apply admin role filter
            if is_admin is not None:
                query = query.where(UserModel.is_admin == is_admin)
            
            # Apply subscription tier filter
            if subscription_tier:
                query = query.where(UserModel.subscription_tier == subscription_tier)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total_count = total_result.scalar() or 0
            
            # Apply pagination and order
            query = query.order_by(UserModel.created_at.desc()).offset(skip).limit(limit)
            
            result = await db.execute(query)
            models = result.scalars().all()
            
            users = [self._to_entity(model) for model in models]
            return users, total_count
    
    async def create(self, user: User) -> User:
        """Create new user"""
        async with async_session_maker() as db:
            model = UserModel(
                id=user.id,
                email=user.email,
                username=user.username,
                password_hash=user.password_hash,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                google_id=user.google_id,
                role=user.role,
                points=user.points,
                balance=user.balance,
                subscription_tier=user.subscription_tier,
                subscription_expires_at=user.subscription_expires_at,
                is_admin=user.is_admin,
                is_active=user.is_active
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
            
            return self._to_entity(model)
    
    async def update(self, user: User) -> User:
        """Update user"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.id == user.id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                raise ValueError("User not found")
            
            # Update allowed fields
            model.full_name = user.full_name
            model.email = user.email
            model.username = user.username
            model.avatar_url = user.avatar_url
            model.is_active = user.is_active
            model.is_admin = user.is_admin
            model.role = user.role
            model.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(model)
            
            return self._to_entity(model)
    
    async def delete(self, user_id: UUID) -> bool:
        """Soft delete user by setting is_active=False"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return False
            
            model.is_active = False
            model.updated_at = datetime.now()
            await db.commit()
            
            return True
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity"""
        return User(
            id=_to_uuid(model.id),
            email=model.email,
            username=model.username,
            password_hash=model.password_hash,
            full_name=model.full_name,
            avatar_url=model.avatar_url,
            google_id=model.google_id,
            role=model.role,
            points=model.points,
            balance=model.balance,
            subscription_tier=model.subscription_tier,
            subscription_expires_at=model.subscription_expires_at,
            is_admin=model.is_admin,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_login_at=model.last_login_at
        )
