# Auth Module - API Routes

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from modules.auth.api.schemas import (
    RegisterRequest, LoginRequest, 
    UserResponse, AuthResponse
)
from modules.auth.providers import get_user_repository, get_jwt_service, get_password_service
from modules.auth.domain.entities import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới"
)
async def register(data: RegisterRequest):
    """Register a new user account"""
    user_repo = get_user_repository()
    jwt_service = get_jwt_service()
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
    
    # Create user
    user = User(
        email=data.email,
        username=data.username,
        password_hash=password_service.hash_password(data.password),
        full_name=data.full_name
    )
    
    created_user = await user_repo.create(user)
    
    # Generate token
    token = jwt_service.create_access_token(
        user_id=str(created_user.id),
        email=created_user.email
    )
    
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(created_user.id),
            email=created_user.email,
            username=created_user.username,
            full_name=created_user.full_name,
            avatar_url=created_user.avatar_url,
            is_active=created_user.is_active,
            created_at=created_user.created_at,
            last_login_at=created_user.last_login_at
        )
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Đăng nhập"
)
async def login(data: LoginRequest):
    """Login with email and password"""
    user_repo = get_user_repository()
    jwt_service = get_jwt_service()
    password_service = get_password_service()
    
    # Find user by email
    user = await user_repo.get_by_email(data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not password_service.verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Update last login
    await user_repo.update_last_login(user.id)
    
    # Generate token
    token = jwt_service.create_access_token(
        user_id=str(user.id),
        email=user.email
    )
    
    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin user hiện tại"
)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user info"""
    jwt_service = get_jwt_service()
    user_repo = get_user_repository()
    
    # Decode token
    token = credentials.credentials
    user_id = jwt_service.get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user
    from uuid import UUID
    user = await user_repo.get_by_id(UUID(user_id))
    
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
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )
