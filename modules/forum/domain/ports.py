# Forum Domain - Ports (Interfaces)
# Repository interfaces following hexagonal architecture

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from uuid import UUID

from modules.forum.domain.entities import (
    ForumCategory, ForumPost, ForumComment, ForumStats, ContributorStats
)


class ForumRepositoryPort(ABC):
    """Interface for forum data access"""
    
    # =====================================================
    # READ Operations
    # =====================================================
    
    @abstractmethod
    async def get_categories(self) -> List[ForumCategory]:
        """Get all forum categories"""
        pass
    
    @abstractmethod
    async def get_category_by_id(self, category_id: UUID) -> Optional[ForumCategory]:
        """Get category by ID"""
        pass
    
    @abstractmethod
    async def get_category_by_slug(self, slug: str) -> Optional[ForumCategory]:
        """Get category by slug"""
        pass
    
    @abstractmethod
    async def get_latest_posts(self, limit: int = 10) -> List[ForumPost]:
        """Get latest posts across all categories"""
        pass
    
    @abstractmethod
    async def get_posts_by_category(self, category_id: UUID, sort_by: str = 'newest', search: str = None, page: int = 1, limit: int = 10, current_user_id: Optional[UUID] = None) -> Tuple[List[ForumPost], int]:
        """Get posts by category with sorting, search, and pagination"""
        pass
    
    @abstractmethod
    async def get_related_posts(self, post_id: UUID, category_id: UUID, limit: int = 5) -> List[ForumPost]:
        """Get related posts (same category, different post)"""
        pass
    
    @abstractmethod
    async def get_post_by_id(self, post_id: UUID) -> Optional[ForumPost]:
        """Get post by ID with author info"""
        pass
    
    @abstractmethod
    async def get_comments_by_post(self, post_id: UUID) -> List[ForumComment]:
        """Get comments for a post"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> ForumStats:
        """Get forum statistics"""
        pass
    
    @abstractmethod
    async def get_like_count(self, post_id: UUID) -> int:
        """Get number of likes for a post"""
        pass
    
    # =====================================================
    # WRITE Operations
    # =====================================================
    
    @abstractmethod
    async def create_post(
        self, user_id: UUID, category_id: UUID, title: str, content: str, images: Optional[List[str]] = None
    ) -> ForumPost:
        """Create a new forum post"""
        pass
    
    @abstractmethod
    async def update_post(
        self, post_id: UUID, user_id: UUID, title: Optional[str] = None, content: Optional[str] = None, category_id: Optional[UUID] = None, images: Optional[List[str]] = None
    ) -> Optional[ForumPost]:
        """Update an existing forum post. Must verify ownership."""
        pass
    
    @abstractmethod
    async def toggle_post_like(self, user_id: UUID, post_id: UUID) -> bool:
        """Toggle like on a post. Returns True if liked, False if unliked."""
        pass
    
    @abstractmethod
    async def has_user_liked_post(self, user_id: UUID, post_id: UUID) -> bool:
        """Check if user has liked a post"""
        pass
    
    @abstractmethod
    async def create_comment(
        self, user_id: UUID, post_id: UUID, content: str, parent_id: Optional[UUID] = None
    ) -> ForumComment:
        """Create a comment on a post, optionally as a reply to another comment"""
        pass
    
    @abstractmethod
    async def get_top_contributors(self, limit: int, month: int, year: int) -> List[ContributorStats]:
        """Get top contributors for a specific month based on scoring system:
        - Create Post: 10 points
        - Write Comment: 2 points
        - Receive Like: 5 points
        """
        pass


