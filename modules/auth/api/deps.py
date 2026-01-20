from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

from modules.auth.providers import get_jwt_service, get_user_repository
from modules.auth.domain.entities import User

security = HTTPBearer()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Extract user ID from JWT token"""
    jwt_service = get_jwt_service()
    
    token = credentials.credentials
    user_id = jwt_service.get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UUID(user_id)

async def get_current_user(user_id: UUID = Depends(get_current_user_id)) -> User:
    """Get full user object from ID"""
    user_repo = get_user_repository()
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )
    
    return user


# Optional auth - returns None if not authenticated
security_optional = HTTPBearer(auto_error=False)

async def get_current_user_id_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_optional)
) -> UUID | None:
    """Extract user ID from JWT token, returns None if not authenticated"""
    if not credentials:
        return None
    
    jwt_service = get_jwt_service()
    token = credentials.credentials
    user_id = jwt_service.get_user_id_from_token(token)
    
    if not user_id:
        return None
    
    return UUID(user_id)

