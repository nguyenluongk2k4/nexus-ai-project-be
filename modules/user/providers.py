# User Module - Dependency Injection Providers

from modules.user.domain.ports import UserRepositoryPort
from modules.user.infrastructure.repository import UserRepositoryImpl
from modules.auth.providers import get_password_service

# Singleton instances
_user_repository: UserRepositoryPort = None


def get_user_repository() -> UserRepositoryPort:
    """Get User Repository singleton"""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepositoryImpl()
    return _user_repository
