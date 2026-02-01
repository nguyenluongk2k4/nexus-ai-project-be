  # Auth Module - API Routes

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from modules.auth.api.schemas import (
    RegisterRequest, LoginRequest, 
    UserResponse, AuthResponse
)
from modules.auth.providers import get_user_repository, get_jwt_service, get_password_service
from modules.auth.domain.entities import User
from modules.auth.api.deps import get_current_user
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])




# ===========================================
# GOOGLE OAUTH ENDPOINTS
# ===========================================

@router.get("/google/login", summary="Get Google Login URL")
async def google_login():
    """Return the Google OAuth login URL"""
    return {
        "url": (
            "https://accounts.google.com/o/oauth2/auth"
            f"?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.API_BASE_URL}/api/auth/google/callback"
            "&scope=openid%20email%20profile"
            "&access_type=offline"
        )
    }


@router.get("/google/callback", summary="Google OAuth Callback")
async def google_callback(code: str):
    """Handle Google OAuth callback code"""
    import httpx
    
    # 1. Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"{settings.API_BASE_URL}/api/auth/google/callback",
        "grant_type": "authorization_code",
    }
    
    try:
        # Set longer timeout (30 seconds) for external API calls
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                print(f"[Google OAuth] Token exchange failed: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Failed to retrieve token from Google"
                )
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            # 2. Get user info
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = user_info_response.json()
    except httpx.TimeoutException as e:
        print(f"[Google OAuth] Timeout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Google authentication timed out. Please try again."
        )
    except httpx.RequestError as e:
        print(f"[Google OAuth] Network error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not connect to Google. Please check your network."
        )
        
    email = user_info.get("email")
    google_id = user_info.get("id")
    full_name = user_info.get("name")
    avatar_url = user_info.get("picture")
    
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user_repo = get_user_repository()
    jwt_service = get_jwt_service()
    
    # 3. Find or Create User
    try:
        user = await user_repo.get_by_email(email)
        
        if user:
            print(f"[DEBUG] Found existing user: {user.email}")
            # Link google_id if not linked
            if not user.google_id:
                print(f"[DEBUG] Linking Google ID for {user.email}")
                user.google_id = google_id
                # Optionally update avatar if missing
                if not user.avatar_url:
                    user.avatar_url = avatar_url
                await user_repo.update(user) 
            else:
                print(f"[DEBUG] User already linked to Google ID: {user.google_id}")
        else:
            print(f"[DEBUG] Creating new user for {email}")
            # Create new user
            # Generate random password for OAuth users
            from modules.auth.domain.entities import User as UserEntity
            import secrets
            
            random_password = secrets.token_urlsafe(16)
            password_service = get_password_service()
            
            # Username from email prefix + random suffix to ensure uniqueness
            base_username = email.split("@")[0]
            # Add longer suffix to ensure uniqueness
            username = f"{base_username}_{secrets.token_hex(4)}"
            
            new_user = UserEntity(
                email=email,
                username=username,
                password_hash=password_service.hash_password(random_password),
                full_name=full_name,
                avatar_url=avatar_url,
                google_id=google_id
            )
            user = await user_repo.create(new_user)
            print(f"[DEBUG] User created: {user.id}")

        # 4. Login (Generate Token)
        token = jwt_service.create_access_token(
            user_id=str(user.id),
            email=user.email
        )
        
        # Redirect to frontend with token
        from fastapi.responses import RedirectResponse
        
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        print(f"[ERROR] Google Callback Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

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
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
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
