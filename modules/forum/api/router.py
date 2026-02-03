# Forum API - Router
# FastAPI endpoints for forum data

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_db
from modules.forum.infrastructure.repository import ForumRepositoryImpl
from modules.auth.api.deps import get_current_user_id_optional


router = APIRouter(prefix="/api/forum", tags=["forum"])


# =====================================================
# Pydantic Response Models
# =====================================================

class UserResponse(BaseModel):
    id: Optional[str]
    username: str
    full_name: Optional[str]
    avatar: Optional[str]
    rank: Optional[str] = None
    
    class Config:
        from_attributes = True


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    sort_order: int
    post_count: int = 0
    # Frontend compatibility fields
    iconName: Optional[str] = None
    color: Optional[str] = None
    
    class Config:
        from_attributes = True


class PostStatsResponse(BaseModel):
    views: int
    comments: int
    likes: int


class PostResponse(BaseModel):
    id: str
    title: str
    excerpt: str
    content: Optional[str] = None
    author: UserResponse
    categoryId: str
    categoryName: Optional[str] = None
    categoryColor: Optional[str] = None
    stats: PostStatsResponse
    createdAt: str
    updatedAt: Optional[str] = None
    isPinned: bool = False
    isHot: bool = False
    isLiked: bool = False  # Whether current user has liked this post
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: str
    postId: str
    parentId: Optional[str] = None  # For replies
    author: UserResponse
    content: str
    likes: int = 0
    createdAt: str
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    totalPosts: int
    totalMembers: int
    onlineMembers: int


class ForumDashboardResponse(BaseModel):
    categories: List[CategoryResponse]
    latestPosts: List[PostResponse]
    stats: StatsResponse


class CategoryPostsResponse(BaseModel):
    category: CategoryResponse
    posts: List[PostResponse]


class ThreadDetailsResponse(BaseModel):
    post: PostResponse
    comments: List[CommentResponse]


# =====================================================
# Icon/Color mapping (to match frontend mock)
# =====================================================

CATEGORY_STYLES = {
    "ai": {"iconName": "Bot", "color": "from-violet-500 to-purple-600"},
    "software": {"iconName": "Code", "color": "from-blue-500 to-cyan-600"},
    "data": {"iconName": "Database", "color": "from-orange-500 to-red-600"},
}


def get_category_style(slug: str) -> dict:
    return CATEGORY_STYLES.get(slug, {"iconName": "MessageSquare", "color": "from-gray-500 to-gray-600"})


# =====================================================
# Helper Functions
# =====================================================

def post_to_response(post, is_liked: bool = False) -> PostResponse:
    """Convert domain post to response"""
    style = get_category_style(post.category_slug or "")
    
    # Create excerpt from content (first 200 chars)
    excerpt = post.content[:200] + "..." if len(post.content) > 200 else post.content
    
    # Determine if hot (more than 100 views or 10 comments)
    is_hot = post.view_count > 100 or post.comment_count > 10
    
    return PostResponse(
        id=str(post.id),
        title=post.title,
        excerpt=excerpt,
        content=post.content,
        author=UserResponse(
            id=str(post.author.id) if post.author.id else None,
            username=post.author.username,
            full_name=post.author.full_name,
            avatar=post.author.avatar,
            rank=post.author.role
        ),
        categoryId=str(post.category_id) if post.category_id else "",
        categoryName=post.category_name,
        categoryColor=style["color"],
        stats=PostStatsResponse(
            views=post.view_count,
            comments=post.comment_count,
            likes=post.like_count
        ),
        createdAt=post.created_at.isoformat() if post.created_at else "",
        updatedAt=post.updated_at.isoformat() if post.updated_at else None,
        isPinned=post.is_pinned,
        isHot=is_hot,
        isLiked=is_liked
    )


def category_to_response(cat) -> CategoryResponse:
    """Convert domain category to response"""
    style = get_category_style(cat.slug)
    return CategoryResponse(
        id=str(cat.id),
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        icon=cat.icon,
        sort_order=cat.sort_order,
        post_count=cat.post_count,
        iconName=style["iconName"],
        color=style["color"]
    )


# =====================================================
# API Endpoints
# =====================================================

@router.get("/dashboard", response_model=ForumDashboardResponse)
async def get_forum_dashboard(db: AsyncSession = Depends(get_db)):
    """Get forum dashboard data: categories, latest posts, stats"""
    repo = ForumRepositoryImpl(db)
    
    categories = await repo.get_categories()
    latest_posts = await repo.get_latest_posts(limit=10)
    stats = await repo.get_stats()
    
    return ForumDashboardResponse(
        categories=[category_to_response(c) for c in categories],
        latestPosts=[post_to_response(p) for p in latest_posts],
        stats=StatsResponse(
            totalPosts=stats.total_posts,
            totalMembers=stats.total_members,
            onlineMembers=stats.online_members
        )
    )


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all forum categories"""
    repo = ForumRepositoryImpl(db)
    categories = await repo.get_categories()
    return [category_to_response(c) for c in categories]


@router.get("/categories/{category_id}/posts", response_model=CategoryPostsResponse)
async def get_posts_by_category(
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get posts in a specific category"""
    repo = ForumRepositoryImpl(db)
    
    # Try to find category by slug first, then by UUID
    category = await repo.get_category_by_slug(category_id)
    if not category:
        try:
            category = await repo.get_category_by_id(UUID(category_id))
        except ValueError:
            pass
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    posts = await repo.get_posts_by_category(category.id)
    
    return CategoryPostsResponse(
        category=category_to_response(category),
        posts=[post_to_response(p) for p in posts]
    )


@router.get("/posts", response_model=List[PostResponse])
async def get_latest_posts(
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get latest posts"""
    repo = ForumRepositoryImpl(db)
    posts = await repo.get_latest_posts(limit=limit)
    return [post_to_response(p) for p in posts]


@router.get("/posts/{post_id}", response_model=ThreadDetailsResponse)
async def get_thread_details(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id_optional)
):
    """Get post details with comments"""
    repo = ForumRepositoryImpl(db)
    
    # The repo now handles both UUID and short-ID formats
    post = await repo.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Use the actual UUID from the found post for comments and like check
    post_uuid = post.id
    comments = await repo.get_comments_by_post(post_uuid)
    
    # Check if current user has liked the post
    is_liked = False
    if user_id:
        is_liked = await repo.has_user_liked_post(user_id, post_uuid)
    
    return ThreadDetailsResponse(
        post=post_to_response(post, is_liked=is_liked),
        comments=[
            CommentResponse(
                id=str(c.id),
                postId=str(c.post_id),
                parentId=str(c.parent_id) if c.parent_id else None,
                author=UserResponse(
                    id=str(c.author.id) if c.author.id else None,
                    username=c.author.username,
                    full_name=c.author.full_name,
                    avatar=c.author.avatar,
                    rank=c.author.role
                ),
                content=c.content,
                likes=0,  # Would need separate like count per comment
                createdAt=c.created_at.isoformat() if c.created_at else ""
            )
            for c in comments
        ]
    )


@router.get("/stats", response_model=StatsResponse)
async def get_forum_stats(db: AsyncSession = Depends(get_db)):
    """Get forum statistics"""
    repo = ForumRepositoryImpl(db)
    stats = await repo.get_stats()
    
    return StatsResponse(
        totalPosts=stats.total_posts,
        totalMembers=stats.total_members,
        onlineMembers=stats.online_members
    )


# =====================================================
# WRITE Endpoints (require authentication)
# =====================================================

from modules.auth.api.deps import get_current_user_id


class CreatePostRequest(BaseModel):
    categoryId: str
    title: str
    content: str


class CreateCommentRequest(BaseModel):
    content: str
    parentId: Optional[str] = None


class LikeResponse(BaseModel):
    liked: bool
    likeCount: int


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    data: CreatePostRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Create a new forum post (requires authentication)"""
    repo = ForumRepositoryImpl(db)
    
    # Validate category exists
    try:
        category_uuid = UUID(data.categoryId)
    except ValueError:
        # Try slug
        cat = await repo.get_category_by_slug(data.categoryId)
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category")
        category_uuid = cat.id
    
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")
    
    post = await repo.create_post(
        user_id=user_id,
        category_id=category_uuid,
        title=data.title.strip(),
        content=data.content.strip()
    )
    
    await db.commit()
    
    return post_to_response(post)


@router.post("/posts/{post_id}/like", response_model=LikeResponse)
async def toggle_post_like(
    post_id: str,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Toggle like on a post (requires authentication)"""
    repo = ForumRepositoryImpl(db)
    
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    # Check post exists
    post = await repo.get_post_by_id(post_uuid)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    liked = await repo.toggle_post_like(user_id=user_id, post_id=post_uuid)
    like_count = await repo.get_like_count(post_uuid)
    
    await db.commit()
    
    return LikeResponse(liked=liked, likeCount=like_count)


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: str,
    data: CreateCommentRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Add a comment to a post (requires authentication)"""
    repo = ForumRepositoryImpl(db)
    
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    # Check post exists
    post = await repo.get_post_by_id(post_uuid)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Comment content is required")
    
    # Parse parent_id if replying
    parent_uuid = None
    if data.parentId:
        try:
            parent_uuid = UUID(data.parentId)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent comment ID")
    
    comment = await repo.create_comment(
        user_id=user_id,
        post_id=post_uuid,
        content=data.content.strip(),
        parent_id=parent_uuid
    )
    
    await db.commit()
    
    return CommentResponse(
        id=str(comment.id),
        postId=str(comment.post_id),
        parentId=str(comment.parent_id) if comment.parent_id else None,
        author=UserResponse(
            id=str(comment.author.id) if comment.author.id else None,
            username=comment.author.username,
            full_name=comment.author.full_name,
            avatar=comment.author.avatar,
            rank=comment.author.role
        ),
        content=comment.content,
        likes=0,
        createdAt=comment.created_at.isoformat() if comment.created_at else ""
    )

