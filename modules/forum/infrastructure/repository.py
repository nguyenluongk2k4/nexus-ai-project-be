# Forum Infrastructure - Repository Implementation
# Implements ForumRepositoryPort using SQLAlchemy async queries

from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from modules.forum.domain.entities import (
    ForumCategory, ForumPost, ForumComment, ForumStats, ForumUser, ContributorStats
)
from modules.forum.domain.ports import ForumRepositoryPort
# Use main table models (after migration from COPY tables)
from modules.forum.infrastructure.models import (
    ForumCategoryModel, ForumPostModel, ForumCommentModel, PostLikeModel
)
from modules.auth.infrastructure.models import UserModel
from modules.auth.domain.enums import ForumRank # Added import for ForumRank


class ForumRepositoryImpl(ForumRepositoryPort):
    """SQLAlchemy implementation of ForumRepositoryPort"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _user_model_to_entity(self, user: UserModel) -> ForumUser:
        """Convert UserModel to ForumUser entity"""
        if not user:
            return ForumUser(
                id=uuid4(), # Changed id=None to id=uuid4()
                username="Anonymous",
                full_name="Người dùng ẩn danh",
                avatar="👤"
            )
        # Calculate dynamic rank using ForumRank Enum
        points = user.points if hasattr(user, 'points') else 0
        rank = ForumRank.from_points(points).value # Refactored rank calculation

        return ForumUser(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            avatar=user.avatar_url if user.avatar_url else "👤",
            role=rank,
            points=points
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
    
    async def get_latest_posts(self, limit: int = 10, current_user_id: Optional[UUID] = None) -> List[ForumPost]:
        """Get latest posts across all categories - OPTIMIZED with JOINs"""
        # Single query with JOINs for author & category, subqueries for counts
        comment_count_subq = (
            select(func.count(ForumCommentModel.id))
            .where(ForumCommentModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )
        
        like_count_subq = (
            select(func.count(PostLikeModel.user_id))
            .where(PostLikeModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )

        # Check if current user liked the post
        is_liked_expr = None
        if current_user_id:
             is_liked_expr = (
                select(1)
                .where(
                    (PostLikeModel.post_id == ForumPostModel.id) & 
                    (PostLikeModel.user_id == current_user_id)
                )
                .correlate(ForumPostModel)
                .exists()
            )
        
        stmt = (
            select(
                ForumPostModel,
                UserModel,
                ForumCategoryModel,
                comment_count_subq.label('comment_count'),
                like_count_subq.label('like_count'),
                # Add is_liked column if user is logged in, else False
                 *( (is_liked_expr.label('is_liked'),) if current_user_id else (False,) )
            )
            .outerjoin(UserModel, ForumPostModel.user_id == UserModel.id)
            .outerjoin(ForumCategoryModel, ForumPostModel.category_id == ForumCategoryModel.id)
            .order_by(ForumPostModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.tuples().all()
        
        posts = []
        for row in rows:
            # Handle variable unpacking based on whether is_liked was queried
            if current_user_id:
                 post, user, category, comment_count, like_count, is_liked = row
            else:
                 post, user, category, comment_count, like_count = row[0], row[1], row[2], row[3], row[4]
                 is_liked = False
            
            author = self._user_model_to_entity(user) if user else self._user_model_to_entity(None)
            
            posts.append(ForumPost(
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
                category_name=category.name if category else None,
                category_slug=category.slug if category else None,
                comment_count=comment_count or 0,
                like_count=like_count or 0,
                is_liked=is_liked
            ))
        
        return posts
    
    async def get_posts_by_category(self, category_id: UUID, current_user_id: Optional[UUID] = None) -> List[ForumPost]:
        """Get posts in a specific category - OPTIMIZED with JOINs"""
        comment_count_subq = (
            select(func.count(ForumCommentModel.id))
            .where(ForumCommentModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )
        
        like_count_subq = (
            select(func.count(PostLikeModel.user_id))
            .where(PostLikeModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )

        # Check if current user liked the post
        is_liked_expr = None
        if current_user_id:
             is_liked_expr = (
                select(1)
                .where(
                    (PostLikeModel.post_id == ForumPostModel.id) & 
                    (PostLikeModel.user_id == current_user_id)
                )
                .correlate(ForumPostModel)
                .exists()
            )
        
        stmt = (
            select(
                ForumPostModel,
                UserModel,
                ForumCategoryModel,
                comment_count_subq.label('comment_count'),
                like_count_subq.label('like_count'),
                *( (is_liked_expr.label('is_liked'),) if current_user_id else (False,) )
            )
            .outerjoin(UserModel, ForumPostModel.user_id == UserModel.id)
            .outerjoin(ForumCategoryModel, ForumPostModel.category_id == ForumCategoryModel.id)
            .where(ForumPostModel.category_id == category_id)
            .order_by(ForumPostModel.is_pinned.desc(), ForumPostModel.created_at.desc())
        )
        
        result = await self.session.execute(stmt)
        rows = result.tuples().all()
        
        posts = []
        for row in rows:
            if current_user_id:
                 post, user, category, comment_count, like_count, is_liked = row
            else:
                 post, user, category, comment_count, like_count = row[0], row[1], row[2], row[3], row[4]
                 is_liked = False
            
            author = self._user_model_to_entity(user) if user else self._user_model_to_entity(None)
            
            posts.append(ForumPost(
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
                category_name=category.name if category else None,
                category_slug=category.slug if category else None,
                comment_count=comment_count or 0,
                like_count=like_count or 0,
                is_liked=is_liked
            ))
        
        return posts
    
    async def _enrich_posts(self, posts: List[ForumPostModel]) -> List[ForumPost]:
        """Add author, category, and counts to posts - OPTIMIZED with batch loading"""
        if not posts:
            return []
        
        # Collect all IDs needed
        post_ids = [p.id for p in posts]
        user_ids = [p.user_id for p in posts if p.user_id]
        category_ids = list(set(p.category_id for p in posts if p.category_id))
        
        # Batch load all users in one query
        users_map = {}
        if user_ids:
            user_stmt = select(UserModel).where(UserModel.id.in_(user_ids))
            user_result = await self.session.execute(user_stmt)
            for user in user_result.scalars().all():
                users_map[user.id] = self._user_model_to_entity(user)
        
        # Batch load all categories in one query
        categories_map = {}
        if category_ids:
            cat_stmt = select(ForumCategoryModel).where(ForumCategoryModel.id.in_(category_ids))
            cat_result = await self.session.execute(cat_stmt)
            for cat in cat_result.scalars().all():
                categories_map[cat.id] = {"name": cat.name, "slug": cat.slug}
        
        # Batch load comment counts in one query
        comment_counts_map = {}
        comment_stmt = (
            select(ForumCommentModel.post_id, func.count(ForumCommentModel.id))
            .where(ForumCommentModel.post_id.in_(post_ids))
            .group_by(ForumCommentModel.post_id)
        )
        comment_result = await self.session.execute(comment_stmt)
        for post_id, count in comment_result.all():
            comment_counts_map[post_id] = count
        
        # Batch load like counts in one query
        like_counts_map = {}
        like_stmt = (
            select(PostLikeModel.post_id, func.count(PostLikeModel.user_id))
            .where(PostLikeModel.post_id.in_(post_ids))
            .group_by(PostLikeModel.post_id)
        )
        like_result = await self.session.execute(like_stmt)
        for post_id, count in like_result.all():
            like_counts_map[post_id] = count
        
        # Build enriched posts from cached data
        enriched = []
        for post in posts:
            # Get author from cache
            author = users_map.get(post.user_id) if post.user_id else None
            if not author:
                author = self._user_model_to_entity(None)
            
            # Get category from cache
            cat_data = categories_map.get(post.category_id) if post.category_id else None
            cat_name = cat_data["name"] if cat_data else None
            cat_slug = cat_data["slug"] if cat_data else None
            
            # Get counts from cache
            comment_count = comment_counts_map.get(post.id, 0)
            like_count = like_counts_map.get(post.id, 0)
            
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
        """Get post by ID with author info - OPTIMIZED with JOINs"""
        comment_count_subq = (
            select(func.count(ForumCommentModel.id))
            .where(ForumCommentModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )
        
        like_count_subq = (
            select(func.count(PostLikeModel.user_id))
            .where(PostLikeModel.post_id == ForumPostModel.id)
            .correlate(ForumPostModel)
            .scalar_subquery()
        )
        
        stmt = (
            select(
                ForumPostModel,
                UserModel,
                ForumCategoryModel,
                comment_count_subq.label('comment_count'),
                like_count_subq.label('like_count')
            )
            .outerjoin(UserModel, ForumPostModel.user_id == UserModel.id)
            .outerjoin(ForumCategoryModel, ForumPostModel.category_id == ForumCategoryModel.id)
        )
        
        # Now that frontend sends UUID strings directly, we just do a simple filter
        try:
            post_uuid = UUID(str(post_id))
            stmt = stmt.where(ForumPostModel.id == post_uuid)
        except (ValueError, AttributeError):
            return None
        
        result = await self.session.execute(stmt)
        row = result.tuples().first()
        
        if not row:
            return None
        
        post, user, category, comment_count, like_count = row[0], row[1], row[2], row[3], row[4]
        author = self._user_model_to_entity(user) if user else self._user_model_to_entity(None)
        
        return ForumPost(
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
            category_name=category.name if category else None,
            category_slug=category.slug if category else None,
            comment_count=comment_count or 0,
            like_count=like_count or 0
        )
    
    async def get_comments_by_post(self, post_id: UUID) -> List[ForumComment]:
        """Get comments for a post - OPTIMIZED with JOIN for authors"""
        stmt = (
            select(ForumCommentModel, UserModel)
            .outerjoin(UserModel, ForumCommentModel.user_id == UserModel.id)
            .where(ForumCommentModel.post_id == post_id)
            .order_by(ForumCommentModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.tuples().all()
        
        comment_list = []
        for row in rows:
            comment = row[0]
            user = row[1] if len(row) > 1 else None
            author = self._user_model_to_entity(user) if user else self._user_model_to_entity(None)
            
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

    async def get_top_members(self, limit: int = 5) -> List[ForumUser]:
        """Get top members by total points from user table"""
        
        # Simple query: get users with highest points
        # Also get their post count for display
        stmt = (
            select(
                UserModel,
                func.count(ForumPostModel.id).label('post_count')
            )
            .outerjoin(ForumPostModel, UserModel.id == ForumPostModel.user_id)
            .where(UserModel.is_active == True)
            .group_by(UserModel.id)
            .order_by(UserModel.points.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.tuples().all()
        
        top_users = []
        for row in rows:
            user, post_count = row
            entity = self._user_model_to_entity(user)
            entity.post_count = int(post_count) if post_count else 0
            # entity.points already set from user model
            top_users.append(entity)
            
        return top_users
    
    async def get_top_contributors(self, limit: int, month: int, year: int) -> List[ContributorStats]:
        """Get top contributors for a specific month with detailed stats
        
        Scoring:
        - Create Post: 10 points
        - Write Comment: 2 points
        - Receive Like: 5 points
        """
        from datetime import datetime
        from calendar import monthrange
        
        # Get first and last day of the target month
        first_day = datetime(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59)
        
        # 1. Count posts in target month
        post_stats = (
            select(
                UserModel.id,
                func.count(ForumPostModel.id).label('posts_count')
            )
            .join(ForumPostModel, UserModel.id == ForumPostModel.user_id)
            .where(
                (ForumPostModel.created_at >= first_day) &
                (ForumPostModel.created_at <= last_day) &
                (UserModel.is_active == True)
            )
            .group_by(UserModel.id)
            .cte('post_stats')
        )

        # 2. Count comments in target month
        comment_stats = (
            select(
                UserModel.id,
                func.count(ForumCommentModel.id).label('comments_count')
            )
            .join(ForumCommentModel, UserModel.id == ForumCommentModel.user_id)
            .where(
                (ForumCommentModel.created_at >= first_day) &
                (ForumCommentModel.created_at <= last_day) &
                (UserModel.is_active == True)
            )
            .group_by(UserModel.id)
            .cte('comment_stats')
        )
        
        # 3. Count received likes in target month
        like_stats = (
            select(
                ForumPostModel.user_id.label('id'),
                func.count(PostLikeModel.user_id).label('likes_received')
            )
            .join(PostLikeModel, ForumPostModel.id == PostLikeModel.post_id)
            .where(
                (PostLikeModel.created_at >= first_day) &
                (PostLikeModel.created_at <= last_day) &
                (ForumPostModel.user_id.isnot(None))
            )
            .group_by(ForumPostModel.user_id)
            .cte('like_stats')
        )
        
        # Combine all stats as a subquery first
        combined_stats = (
            select(
                UserModel.id,
                UserModel.username,
                UserModel.avatar_url,
                func.coalesce(post_stats.c.posts_count, 0).label('posts_count'),
                func.coalesce(comment_stats.c.comments_count, 0).label('comments_count'),
                func.coalesce(like_stats.c.likes_received, 0).label('likes_received'),
                (
                    (func.coalesce(post_stats.c.posts_count, 0) * 10) +
                    (func.coalesce(comment_stats.c.comments_count, 0) * 2) +
                    (func.coalesce(like_stats.c.likes_received, 0) * 5)
                ).label('total_points')
            )
            .outerjoin(post_stats, UserModel.id == post_stats.c.id)
            .outerjoin(comment_stats, UserModel.id == comment_stats.c.id)
            .outerjoin(like_stats, UserModel.id == like_stats.c.id)
            .where(UserModel.is_active == True)
            .subquery()
        )
        
        # Now select from subquery and filter/order
        stmt = (
            select(combined_stats)
            .where(combined_stats.c.total_points > 0)
            .order_by(combined_stats.c.total_points.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        contributors = []
        for row in rows:
            contributors.append(ContributorStats(
                user_id=row.id,
                username=row.username,
                avatar=row.avatar_url if row.avatar_url else "👤",
                total_points=int(row.total_points),
                posts_count=int(row.posts_count),
                comments_count=int(row.comments_count),
                likes_received=int(row.likes_received)
            ))
        
        return contributors
        
        
    async def increment_view_count(self, post_id: UUID) -> None:
        """Increment view count for a post"""
        from sqlalchemy import update
        
        stmt = (
            update(ForumPostModel)
            .where(ForumPostModel.id == post_id)
            .values(view_count=ForumPostModel.view_count + 1)
        )
        
        await self.session.execute(stmt)
        await self.session.commit()

