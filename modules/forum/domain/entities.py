# Forum Domain - Entities
# Pure domain objects without framework dependencies

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID


@dataclass
class ForumUser:
    """User info for forum display"""
    id: UUID
    username: str
    full_name: Optional[str]
    avatar: Optional[str]  # emoji or URL
    role: Optional[str] = "member"
    points: int = 0
    post_count: int = 0


@dataclass
class ForumCategory:
    """Forum category/subforum"""
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    icon: Optional[str]
    sort_order: int = 0
    post_count: int = 0


@dataclass
class ForumPost:
    """Forum post/thread"""
    id: UUID
    category_id: UUID
    user_id: Optional[UUID]
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    view_count: int = 0
    is_pinned: bool = False
    is_locked: bool = False
    created_at: datetime = None
    updated_at: datetime = None
    
    # Computed/joined fields
    author: Optional[ForumUser] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    comment_count: int = 0
    like_count: int = 0
    is_liked: bool = False


@dataclass
class ForumComment:
    """Comment on a forum post"""
    id: UUID
    post_id: UUID
    user_id: Optional[UUID]
    parent_id: Optional[UUID]  # For nested comments
    content: str
    created_at: datetime = None
    updated_at: datetime = None
    
    # Computed/joined fields
    author: Optional[ForumUser] = None
    replies: List['ForumComment'] = None


@dataclass
class PostLike:
    """Like on a forum post"""
    user_id: UUID
    post_id: UUID
    created_at: datetime = None


@dataclass
class ForumStats:
    """Forum statistics"""
    total_posts: int
    total_members: int
    online_members: int


@dataclass
class ContributorStats:
    """Monthly contributor statistics for leaderboard"""
    user_id: UUID
    username: str
    avatar: Optional[str]
    total_points: int
    posts_count: int
    comments_count: int
    likes_received: int
