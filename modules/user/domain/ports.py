# User Module - Domain Ports (Interfaces)

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from modules.auth.domain.entities import User


class UserRepositoryPort(ABC):
    """Interface for User management data access"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        subscription_tier: Optional[str] = None
    ) -> tuple[List[User], int]:
        """Get all users with pagination and optional filters. Returns (users, total_count)"""
        pass
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Create new user"""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user (soft delete by setting is_active=False)"""
        pass
