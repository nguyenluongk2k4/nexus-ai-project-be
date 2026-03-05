# Forum Infrastructure - SQLAlchemy Models
# Database models for main forum tables

from datetime import datetime
from typing import Optional
from uuid import uuid4
import uuid as uuid_module

from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.connection import Base


# =====================================================
# Main Table Models (used after migration)
# =====================================================

class ForumCategoryModel(Base):
    """Forum category model"""
    __tablename__ = "forum_categories"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    posts = relationship("ForumPostModel", back_populates="category")


class ForumPostModel(Base):
    """Forum post model"""
    __tablename__ = "forum_posts"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_categories.id")
    )
    user_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    category = relationship("ForumCategoryModel", back_populates="posts")
    comments = relationship("ForumCommentModel", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLikeModel", back_populates="post", cascade="all, delete-orphan")


class ForumCommentModel(Base):
    """Forum comment model"""
    __tablename__ = "forum_comments"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="CASCADE")
    )
    user_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    parent_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_comments.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    post = relationship("ForumPostModel", back_populates="comments")
    replies = relationship("ForumCommentModel", backref="parent", remote_side=[id])


class PostLikeModel(Base):
    """Post like model"""
    __tablename__ = "post_likes"
    
    user_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    post = relationship("ForumPostModel", back_populates="likes")


# =====================================================
# COPY Table Models (kept for reference, can be removed)
# =====================================================

class ForumCategoryCopyModel(Base):
    """Forum category COPY table model - for seeding only"""
    __tablename__ = "forum_categories_copy"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ForumPostCopyModel(Base):
    """Forum post COPY table model - for seeding only"""
    __tablename__ = "forum_posts_copy"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ForumCommentCopyModel(Base):
    """Forum comment COPY table model - for seeding only"""
    __tablename__ = "forum_comments_copy"
    __table_args__ = {'extend_existing': True}
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True))
    parent_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PostLikeCopyModel(Base):
    """Post like COPY table model - for seeding only"""
    __tablename__ = "post_likes_copy"
    __table_args__ = {'extend_existing': True}
    
    user_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    post_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

