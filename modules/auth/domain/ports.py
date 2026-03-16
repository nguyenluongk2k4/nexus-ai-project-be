# Auth Module - Domain Ports (Interfaces)

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from modules.auth.domain.entities import User


class AuthRepositoryPort(ABC):
    """Interface for User data access"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def create(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def update_last_login(self, user_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def update_tour_status(self, user_id: UUID, status: bool, phase: str = "all") -> None:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass
