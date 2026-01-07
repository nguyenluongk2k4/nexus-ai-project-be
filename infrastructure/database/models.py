# Infrastructure - SQLAlchemy Models
# Database models mapping to domain entities

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, ForeignKey, 
    Enum as SQLEnum, JSON, Date
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database.connection import Base


# ============================================================
# USER MODEL
# ============================================================

class UserModel(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    chat_sessions: Mapped[List["ChatSessionModel"]] = relationship(back_populates="user")
    skill_trees: Mapped[List["UserSkillTreeModel"]] = relationship(back_populates="user")


# ============================================================
# CHAT MODELS
# ============================================================

class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user: Mapped[Optional["UserModel"]] = relationship(back_populates="chat_sessions")
    messages: Mapped[List["MessageModel"]] = relationship(back_populates="session", order_by="MessageModel.created_at")


class MessageModel(Base):
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    session: Mapped["ChatSessionModel"] = relationship(back_populates="messages")


# ============================================================
# SKILL TREE TEMPLATE MODELS
# ============================================================

class SkillTreeTemplateModel(Base):
    __tablename__ = "skill_tree_templates"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    nodes: Mapped[List["TemplateSkillNodeModel"]] = relationship(back_populates="template")


class TemplateSkillNodeModel(Base):
    __tablename__ = "template_skill_nodes"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    template_id: Mapped[str] = mapped_column(String(36), ForeignKey("skill_tree_templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    node_type: Mapped[str] = mapped_column(String(20), default="knowledge")  # specialization, ability, skill, knowledge
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20))
    estimated_hours: Mapped[Optional[int]] = mapped_column(Integer)
    position_x: Mapped[Optional[int]] = mapped_column(Integer)
    position_y: Mapped[Optional[int]] = mapped_column(Integer)
    keywords: Mapped[Optional[dict]] = mapped_column(JSON)  # Store as JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    template: Mapped["SkillTreeTemplateModel"] = relationship(back_populates="nodes")
    resources: Mapped[List["LearningResourceModel"]] = relationship(back_populates="skill_node")


class TemplateSkillPathModel(Base):
    """Closure table for template skill tree hierarchy"""
    __tablename__ = "template_skill_paths"
    
    ancestor_id: Mapped[str] = mapped_column(String(36), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    descendant_id: Mapped[str] = mapped_column(String(36), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


# ============================================================
# USER SKILL TREE MODELS
# ============================================================

class UserSkillTreeModel(Base):
    __tablename__ = "user_skill_trees"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    template_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("skill_tree_templates.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="skill_trees")
    nodes: Mapped[List["UserSkillNodeModel"]] = relationship(back_populates="tree")


class UserSkillNodeModel(Base):
    __tablename__ = "user_skill_nodes"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tree_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_skill_trees.id", ondelete="CASCADE"))
    original_node_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("template_skill_nodes.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    position_x: Mapped[Optional[int]] = mapped_column(Integer)
    position_y: Mapped[Optional[int]] = mapped_column(Integer)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    tree: Mapped["UserSkillTreeModel"] = relationship(back_populates="nodes")


class UserSkillPathModel(Base):
    """Closure table for user skill tree hierarchy"""
    __tablename__ = "user_skill_paths"
    
    ancestor_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    descendant_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


# ============================================================
# LEARNING MODELS
# ============================================================

class LearningResourceModel(Base):
    __tablename__ = "learning_resources"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    skill_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    resource_type: Mapped[str] = mapped_column(String(50), default="article")
    platform: Mapped[Optional[str]] = mapped_column(String(100))
    estimated_duration: Mapped[Optional[int]] = mapped_column(Integer)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    skill_node: Mapped["TemplateSkillNodeModel"] = relationship(back_populates="resources")


class LearningProgressModel(Base):
    __tablename__ = "learning_progress"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    resource_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_resources.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="not_started")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class StudySessionModel(Base):
    __tablename__ = "study_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))
    resource_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_resources.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ============================================================
# FORUM MODELS
# ============================================================

class ForumCategoryModel(Base):
    __tablename__ = "forum_categories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    posts: Mapped[List["ForumPostModel"]] = relationship(back_populates="category")


class ForumPostModel(Base):
    __tablename__ = "forum_posts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("forum_categories.id"))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    category: Mapped["ForumCategoryModel"] = relationship(back_populates="posts")
    comments: Mapped[List["ForumCommentModel"]] = relationship(back_populates="post")


class ForumCommentModel(Base):
    __tablename__ = "forum_comments"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey("forum_posts.id", ondelete="CASCADE"))
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("forum_comments.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    post: Mapped["ForumPostModel"] = relationship(back_populates="comments")


# ============================================================
# JOB MODELS
# ============================================================

class JobModel(Base):
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    job_type: Mapped[str] = mapped_column(String(50), default="full-time")
    experience_level: Mapped[str] = mapped_column(String(50), default="mid")
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD")
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    benefits: Mapped[Optional[str]] = mapped_column(Text)
    apply_url: Mapped[Optional[str]] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
