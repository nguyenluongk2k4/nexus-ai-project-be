# User Module - API Dependencies

from fastapi import Depends, HTTPException, status

from modules.auth.domain.entities import User
from modules.auth.api.deps import get_current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
