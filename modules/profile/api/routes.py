# Profile Module - API Routes
# Endpoints for user profile and stats

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

from modules.auth.api.deps import get_current_user
from modules.auth.domain.entities import User
from shared.database.connection import get_db
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
# Coins integration
from modules.coins.infrastructure.repository import SQLAlchemyMissionRepository, SQLAlchemyCoinsRepository
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.services.mission_service import MissionService


router = APIRouter(prefix="/profile", tags=["Profile"])


# ============================================================
# SCHEMAS
# ============================================================

class ProfileResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]
    is_active: bool
    balance: float = 0.0
    subscription_tier: str = "free"
    subscription_tier_name: str = "Free"
    subscription_expires_at: Optional[datetime] = None
    streak: int = 0

    class Config:
        from_attributes = True


class ProfileStatsResponse(BaseModel):
    learning_hours: float
    skills_completed: int
    streak_days: int
    forum_posts: int


class ActivityItemResponse(BaseModel):
    id: str
    type: str  # login, skill_complete, purchase, forum_post, learning
    description: str
    timestamp: datetime


class FullProfileResponse(BaseModel):
    profile: ProfileResponse
    stats: ProfileStatsResponse
    activities: list[ActivityItemResponse]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Lấy thông tin profile của user hiện tại"
)
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get current user's profile information"""
    # Query balance and subscription from database
    result = await session.execute(
        text("""
            SELECT 
                COALESCE(u.balance, 0) as balance,
                COALESCE(u.subscription_tier, 'free') as tier,
                u.subscription_expires_at,
                COALESCE(sp.name, 'Free') as tier_name
            FROM users u
            LEFT JOIN subscription_plans sp ON u.subscription_tier = sp.id
            WHERE u.id = :user_id
        """),
        {"user_id": str(user.id)}
    )
    row = result.fetchone()
    
    balance = float(row.balance) if row else 0
    tier = row.tier if row else "free"
    tier_name = row.tier_name if row else "Free"
    expires_at = row.subscription_expires_at if row else None
    
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        is_active=user.is_active,
        balance=balance,
        subscription_tier=tier,
        subscription_tier_name=tier_name,
        subscription_expires_at=expires_at,
        streak=user.streak
    )


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


@router.put(
    "/me",
    response_model=ProfileResponse,
    summary="Cập nhật thông tin profile"
)
async def update_profile(
    data: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Update current user's profile information"""
    from modules.auth.providers import get_user_repository
    
    user_repo = get_user_repository()
    
    # Update fields if provided
    print(f"[DEBUG Profile Update] Received data: {data}")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.avatar_url is not None:
        print(f"[DEBUG Profile Update] Updating avatar_url to: {data.avatar_url}")
        user.avatar_url = data.avatar_url
    
    # Update timestamp
    from datetime import datetime
    user.updated_at = datetime.now()
    
    # Save to database
    updated_user = await user_repo.update(user)
    
    # Coins Integration: Reward for profile update
    try:
        coins_repo = SQLAlchemyCoinsRepository(session)
        coins_service = CoinsService(coins_repo)
        mission_repo = SQLAlchemyMissionRepository(session)
        mission_service = MissionService(mission_repo, coins_service)
        
        await mission_service.update_progress(
            user_id=user.id,
            mission_type='update_profile',
            progress_data={'completed': True}
        )
    except Exception as e:
        # Don't fail the profile update if coins award fails
        print(f"Failed to award coins for profile update: {e}")

    return ProfileResponse(
        id=str(updated_user.id),
        email=updated_user.email,
        username=updated_user.username,
        full_name=updated_user.full_name,
        avatar_url=updated_user.avatar_url,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        last_login_at=updated_user.last_login_at,
        is_active=updated_user.is_active,
        balance=updated_user.balance,
        streak=updated_user.streak
    )


@router.get(
    "/stats",
    response_model=ProfileStatsResponse,
    summary="Lấy thống kê học tập của user"
)
async def get_profile_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user's learning statistics"""
    user_id = user.id
    
    # Query learning hours from study_sessions
    learning_hours_result = await session.execute(
        text("""
            SELECT COALESCE(SUM(duration_minutes), 0) / 60.0 as hours
            FROM study_sessions
            WHERE user_id = :user_id
        """),
        {"user_id": str(user_id)}
    )
    learning_hours = learning_hours_result.scalar() or 0.0
    
    # Query completed skills from user_skill_nodes
    skills_result = await session.execute(
        text("""
            SELECT COUNT(*) as count
            FROM user_skill_nodes
            WHERE tree_id IN (
                SELECT id FROM user_skill_trees WHERE user_id = :user_id
            )
            AND status = 'completed'
        """),
        {"user_id": str(user_id)}
    )
    skills_completed = skills_result.scalar() or 0
    
    # Query forum posts count
    forum_result = await session.execute(
        text("""
            SELECT COUNT(*) as count
            FROM forum_posts
            WHERE user_id = :user_id
        """),
        {"user_id": str(user_id)}
    )
    forum_posts = forum_result.scalar() or 0
    
    # TODO: Calculate streak days from study_sessions (consecutive days with learning)
    streak_days = user.streak
    
    return ProfileStatsResponse(
        learning_hours=round(learning_hours, 1),
        skills_completed=skills_completed,
        streak_days=streak_days,
        forum_posts=forum_posts
    )


@router.get(
    "/activities",
    response_model=list[ActivityItemResponse],
    summary="Lấy lịch sử hoạt động của user"
)
async def get_profile_activities(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 10
):
    """Get user's recent activity history"""
    user_id = user.id
    activities = []
    
    # Get recent forum posts
    posts_result = await session.execute(
        text("""
            SELECT id, title, created_at
            FROM forum_posts
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"user_id": str(user_id), "limit": limit}
    )
    
    for row in posts_result.fetchall():
        activities.append(ActivityItemResponse(
            id=str(row.id),
            type="forum_post",
            description=f'Tạo bài viết: "{row.title[:50]}..."' if len(row.title) > 50 else f'Tạo bài viết: "{row.title}"',
            timestamp=row.created_at
        ))
    
    # Get recent study sessions
    study_result = await session.execute(
        text("""
            SELECT ss.id, ss.started_at, ss.duration_minutes, lr.title as resource_title
            FROM study_sessions ss
            LEFT JOIN learning_resources lr ON ss.resource_id = lr.id
            WHERE ss.user_id = :user_id
            ORDER BY ss.started_at DESC
            LIMIT :limit
        """),
        {"user_id": str(user_id), "limit": limit}
    )
    
    for row in study_result.fetchall():
        hours = (row.duration_minutes or 0) / 60
        activities.append(ActivityItemResponse(
            id=str(row.id),
            type="learning",
            description=f"Học {hours:.1f} giờ" + (f": {row.resource_title}" if row.resource_title else ""),
            timestamp=row.started_at
        ))
    
    # Sort all activities by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    return activities[:limit]


@router.get(
    "/full",
    response_model=FullProfileResponse,
    summary="Lấy toàn bộ thông tin profile (profile + stats + activities)"
)
async def get_full_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get complete profile with stats and activities in one call"""
    profile = await get_profile(user)
    stats = await get_profile_stats(user, session)
    activities = await get_profile_activities(user, session)
    
    return FullProfileResponse(
        profile=profile,
        stats=stats,
        activities=activities
    )
