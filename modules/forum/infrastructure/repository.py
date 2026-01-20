# Forum Infrastructure - Repository Implementation
# Implements ForumRepositoryPort using SQLAlchemy async queries

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from modules.forum.domain.entities import (
    ForumCategory, ForumPost, ForumComment, ForumStats, ForumUser
)
from modules.forum.domain.ports import ForumRepositoryPort
# Use main table models (after migration from COPY tables)
from modules.forum.infrastructure.models import (
    ForumCategoryModel, ForumPostModel, ForumCommentModel, PostLikeModel
)
from modules.auth.infrastructure.models import UserModel


class ForumRepositoryImpl(ForumRepositoryPort):
    """SQLAlchemy implementation of ForumRepositoryPort"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _user_model_to_entity(self, user: UserModel) -> ForumUser:
        """Convert UserModel to ForumUser entity"""
        if not user:
            return ForumUser(
                id=None,
                username="Anonymous",
                full_name="Người dùng ẩn danh",
                avatar="👤"
            )
        return ForumUser(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            avatar=user.avatar_url if user.avatar_url else "👤"
        )
    
    async def get_categories(self) -> List[ForumCategory]:
        """Get all forum categories with post counts"""
        stmt = select(ForumCategoryModel).order_by(ForumCategoryModel.sort_order)
        result = await self.session.execute(stmt)
        categories = result.scalars().all()
        
        category_list = []
        for cat in categories:
            # Get post count
            count_stmt = select(func.count(ForumPostModel.id)).where(
                ForumPostModel.category_id == cat.id
            )
            count_result = await self.session.execute(count_stmt)
            post_count = count_result.scalar() or 0
            
            category_list.append(ForumCategory(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                icon=cat.icon,
                sort_order=cat.sort_order,
                post_count=post_count
            ))
        
        return category_list
    
    async def get_category_by_id(self, category_id: UUID) -> Optional[ForumCategory]:
        """Get category by ID"""
        stmt = select(ForumCategoryModel).where(ForumCategoryModel.id == category_id)
        result = await self.session.execute(stmt)
        cat = result.scalar_one_or_none()
        
        if not cat:
            return None
            
        return ForumCategory(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            sort_order=cat.sort_order
        )
    
    async def get_category_by_slug(self, slug: str) -> Optional[ForumCategory]:
        """Get category by slug"""
        stmt = select(ForumCategoryModel).where(ForumCategoryModel.slug == slug)
        result = await self.session.execute(stmt)
        cat = result.scalar_one_or_none()
        
        if not cat:
            return None
            
        return ForumCategory(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            sort_order=cat.sort_order
        )
    
    async def get_latest_posts(self, limit: int = 10) -> List[ForumPost]:
        """Get latest posts across all categories"""
        stmt = (
            select(ForumPostModel)
            .order_by(ForumPostModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        posts = result.scalars().all()
        
        return await self._enrich_posts(posts)
    
    async def get_posts_by_category(self, category_id: UUID) -> List[ForumPost]:
        """Get posts in a specific category"""
        stmt = (
            select(ForumPostModel)
            .where(ForumPostModel.category_id == category_id)
            .order_by(ForumPostModel.is_pinned.desc(), ForumPostModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        posts = result.scalars().all()
        
        return await self._enrich_posts(posts)
    
    async def _enrich_posts(self, posts: List[ForumPostModel]) -> List[ForumPost]:
        """Add author, category, and counts to posts"""
        enriched = []
        for post in posts:
            # Get author
            author = None
            if post.user_id:
                user_stmt = select(UserModel).where(UserModel.id == post.user_id)
                user_result = await self.session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                author = self._user_model_to_entity(user)
            else:
                author = self._user_model_to_entity(None)
            
            # Get category
            cat_name = None
            cat_slug = None
            if post.category_id:
                cat_stmt = select(ForumCategoryModel).where(
                    ForumCategoryModel.id == post.category_id
                )
                cat_result = await self.session.execute(cat_stmt)
                cat = cat_result.scalar_one_or_none()
                if cat:
                    cat_name = cat.name
                    cat_slug = cat.slug
            
            # Get counts
            comment_count = await self._get_comment_count(post.id)
            like_count = await self.get_like_count(post.id)
            
            enriched.append(ForumPost(
                id=post.id,
                category_id=post.category_id,
                user_id=post.user_id,
                title=post.title,
                content=post.content,
                view_count=post.view_count,
                is_pinned=post.is_pinned,
                is_locked=post.is_locked,
                created_at=post.created_at,
                updated_at=post.updated_at,
                author=author,
                category_name=cat_name,
                category_slug=cat_slug,
                comment_count=comment_count,
                like_count=like_count
            ))
        
        return enriched
    
    async def _get_comment_count(self, post_id: UUID) -> int:
        """Get comment count for a post"""
        stmt = select(func.count(ForumCommentModel.id)).where(
            ForumCommentModel.post_id == post_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_post_by_id(self, post_id: UUID) -> Optional[ForumPost]:
        """Get post by ID with author info"""
        stmt = select(ForumPostModel).where(ForumPostModel.id == post_id)
        result = await self.session.execute(stmt)
        post = result.scalar_one_or_none()
        
        if not post:
            return None
        
        posts = await self._enrich_posts([post])
        return posts[0] if posts else None
    
    async def get_comments_by_post(self, post_id: UUID) -> List[ForumComment]:
        """Get comments for a post (flat list, client can nest)"""
        stmt = (
            select(ForumCommentModel)
            .where(ForumCommentModel.post_id == post_id)
            .order_by(ForumCommentModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        comments = result.scalars().all()
        
        comment_list = []
        for comment in comments:
            # Get author
            author = None
            if comment.user_id:
                user_stmt = select(UserModel).where(UserModel.id == comment.user_id)
                user_result = await self.session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                author = self._user_model_to_entity(user)
            else:
                author = self._user_model_to_entity(None)
            
            comment_list.append(ForumComment(
                id=comment.id,
                post_id=comment.post_id,
                user_id=comment.user_id,
                parent_id=comment.parent_id,
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                author=author,
                replies=[]
            ))
        
        return comment_list
    
    async def get_stats(self) -> ForumStats:
        """Get forum statistics"""
        # Total posts
        post_count_stmt = select(func.count(ForumPostModel.id))
        post_result = await self.session.execute(post_count_stmt)
        total_posts = post_result.scalar() or 0
        
        # Total members (from users table)
        member_count_stmt = select(func.count(UserModel.id)).where(UserModel.is_active == True)
        member_result = await self.session.execute(member_count_stmt)
        total_members = member_result.scalar() or 0
        
        # Online members (mock - would need session tracking in real app)
        online_members = max(1, total_members // 10)
        
        return ForumStats(
            total_posts=total_posts,
            total_members=total_members,
            online_members=online_members
        )
    
    async def get_like_count(self, post_id: UUID) -> int:
        """Get number of likes for a post"""
        stmt = select(func.count(PostLikeModel.user_id)).where(
            PostLikeModel.post_id == post_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    # =====================================================
    # WRITE Operations
    # =====================================================
    
    async def create_post(
        self, user_id: UUID, category_id: UUID, title: str, content: str
    ) -> ForumPost:
        """Create a new forum post"""
        from datetime import datetime
        
        post = ForumPostModel(
            user_id=user_id,
            category_id=category_id,
            title=title,
            content=content,
            view_count=0,
            is_pinned=False,
            is_locked=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.session.add(post)
        await self.session.flush()
        await self.session.refresh(post)
        
        # Return enriched post
        posts = await self._enrich_posts([post])
        return posts[0] if posts else None
    
    async def toggle_post_like(self, user_id: UUID, post_id: UUID) -> bool:
        """Toggle like on a post. Returns True if liked, False if unliked."""
        from datetime import datetime
        
        # Check if already liked
        stmt = select(PostLikeModel).where(
            PostLikeModel.user_id == user_id,
            PostLikeModel.post_id == post_id
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Unlike - remove the like
            await self.session.delete(existing)
            await self.session.flush()
            return False
        else:
            # Like - add new like
            like = PostLikeModel(
                user_id=user_id,
                post_id=post_id,
                created_at=datetime.now()
            )
            self.session.add(like)
            await self.session.flush()
            return True
    
    async def has_user_liked_post(self, user_id: UUID, post_id: UUID) -> bool:
        """Check if user has liked a post"""
        stmt = select(PostLikeModel).where(
            PostLikeModel.user_id == user_id,
            PostLikeModel.post_id == post_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def create_comment(
        self, user_id: UUID, post_id: UUID, content: str, parent_id: Optional[UUID] = None
    ) -> ForumComment:
        """Create a comment on a post, optionally as a reply to another comment"""
        from datetime import datetime
        
        comment = ForumCommentModel(
            user_id=user_id,
            post_id=post_id,
            parent_id=parent_id,
            content=content,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        
        # Get author info
        author = None
        if user_id:
            user_stmt = select(UserModel).where(UserModel.id == user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            author = self._user_model_to_entity(user)
        else:
            author = self._user_model_to_entity(None)
        
        return ForumComment(
            id=comment.id,
            post_id=comment.post_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author=author,
            replies=[]
        )

