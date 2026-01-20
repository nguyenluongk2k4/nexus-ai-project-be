# Auth Module - User Repository Implementation

from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select

from modules.auth.domain.entities import User
from modules.auth.domain.ports import AuthRepositoryPort
from modules.auth.infrastructure.models import UserModel
from shared.database.connection import async_session_maker


def _to_uuid(value) -> UUID:
    """Safely convert value to UUID"""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class UserRepositoryImpl(AuthRepositoryPort):
    """SQLAlchemy implementation of AuthRepositoryPort"""
    
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
                is_active=user.is_active
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
            
            return self._to_entity(model)
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login time"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            
            if model:
                model.last_login_at = datetime.now()
                await db.commit()
    
    async def update(self, user: User) -> User:
        """Update user profile"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(UserModel).where(UserModel.id == user.id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                raise ValueError("User not found")
            
            # Update fields
            model.full_name = user.full_name
            model.email = user.email
            model.avatar_url = user.avatar_url
            model.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(model)
            
            return self._to_entity(model)
    
    def _to_entity(self, model: UserModel) -> User:
        """Convert model to entity"""
        return User(
            id=_to_uuid(model.id),
            email=model.email,
            username=model.username,
            password_hash=model.password_hash,
            full_name=model.full_name,
            avatar_url=model.avatar_url,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_login_at=model.last_login_at
        )
