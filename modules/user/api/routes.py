# User Module - API Routes

from fastapi import APIRouter, HTTPException, Depends, status, Query
from uuid import UUID

from modules.user.api.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserListResponse
)
from modules.user.api.deps import require_admin
from modules.user.providers import get_user_repository
from modules.auth.providers import get_password_service
from modules.auth.domain.entities import User

router = APIRouter(prefix="/admin/users", tags=["Admin - User Management"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="Get all users with pagination and filters"
)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None, description="Search by email, username or full name"),
    is_active: bool = Query(None, description="Filter by active status"),
    is_admin: bool = Query(None, description="Filter by admin role"),
    subscription_tier: str = Query(None, description="Filter by subscription tier"),
    _: User = Depends(require_admin)
):
    """Get list of all users with pagination, search and filters"""
    user_repo = get_user_repository()
    
    skip = (page - 1) * page_size
    users, total = await user_repo.get_all(
        skip=skip, 
        limit=page_size, 
        search=search,
        is_active=is_active,
        is_admin=is_admin,
        subscription_tier=subscription_tier
    )
    
    return UserListResponse(
        users=[
            UserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                balance=user.balance,
                subscription_tier=user.subscription_tier,
                subscription_expires_at=user.subscription_expires_at,
                is_admin=user.is_admin,
                role=user.role,
                points=user.points,
                forum_rank=user.forum_rank,
                created_at=user.created_at,
                last_login_at=user.last_login_at
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID"
)
async def get_user(
    user_id: UUID,
    _: User = Depends(require_admin)
):
    """Get detailed information about a specific user"""
    user_repo = get_user_repository()
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        balance=user.balance,
        subscription_tier=user.subscription_tier,
        subscription_expires_at=user.subscription_expires_at,
        is_admin=user.is_admin,
        role=user.role,
        points=user.points,
        forum_rank=user.forum_rank,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user"
)
async def create_user(
    data: CreateUserRequest,
    _: User = Depends(require_admin)
):
    """Create a new user (admin only)"""
    user_repo = get_user_repository()
    password_service = get_password_service()
    
    # Check if email already exists
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing = await user_repo.get_by_username(data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user entity
    new_user = User(
        email=data.email,
        username=data.username,
        password_hash=password_service.hash_password(data.password),
        full_name=data.full_name,
        is_admin=data.is_admin,
        is_active=data.is_active
    )
    
    created_user = await user_repo.create(new_user)
    
    return UserResponse(
        id=str(created_user.id),
        email=created_user.email,
        username=created_user.username,
        full_name=created_user.full_name,
        avatar_url=created_user.avatar_url,
        is_active=created_user.is_active,
        balance=created_user.balance,
        subscription_tier=created_user.subscription_tier,
        subscription_expires_at=created_user.subscription_expires_at,
        is_admin=created_user.is_admin,
        role=created_user.role,
        points=created_user.points,
        forum_rank=created_user.forum_rank,
        created_at=created_user.created_at,
        last_login_at=created_user.last_login_at
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user"
)
async def update_user(
    user_id: UUID,
    data: UpdateUserRequest,
    _: User = Depends(require_admin)
):
    """Update user information (admin only)"""
    user_repo = get_user_repository()
    
    # Get existing user
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    
    updated_user = await user_repo.update(user)
    
    return UserResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        username=updated_user.username,
        full_name=updated_user.full_name,
        avatar_url=updated_user.avatar_url,
        is_active=updated_user.is_active,
        balance=updated_user.balance,
        subscription_tier=updated_user.subscription_tier,
        subscription_expires_at=updated_user.subscription_expires_at,
        is_admin=updated_user.is_admin,
        role=updated_user.role,
        points=updated_user.points,
        forum_rank=updated_user.forum_rank,
        created_at=updated_user.created_at,
        last_login_at=updated_user.last_login_at
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user (soft delete)"
)
async def delete_user(
    user_id: UUID,
    _: User = Depends(require_admin)
):
    """Soft delete user by setting is_active=False"""
    user_repo = get_user_repository()
    
    success = await user_repo.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return None
