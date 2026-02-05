# Auth Module - Providers (Dependency Injection)

from functools import lru_cache

from modules.auth.infrastructure.repository import UserRepositoryImpl
from modules.auth.usecases.complete_tour import CompleteTourUseCase
from shared.security.jwt_service import JWTService, PasswordService


@lru_cache()
def get_jwt_service() -> JWTService:
    """Get JWT service instance (singleton)"""
    return JWTService()


@lru_cache()
def get_password_service() -> PasswordService:
    """Get password service instance (singleton)"""
    return PasswordService()


def get_user_repository() -> UserRepositoryImpl:
    """Get user repository instance"""
    return UserRepositoryImpl()


def get_complete_tour_use_case() -> CompleteTourUseCase:
    """Get complete tour use case instance"""
    return CompleteTourUseCase(get_user_repository())
