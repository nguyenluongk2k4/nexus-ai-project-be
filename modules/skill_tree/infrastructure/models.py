# Skill Tree Module - Database Models (Infrastructure Layer)
# Following DDD-lite: Models belong to their domain module
# NOTE: These models must match the database schema in database_schema.sql

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import uuid as uuid_module

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.connection import Base


class SkillTreeTemplateModel(Base):
    """Skill Tree Template - represents a complete skill tree structure"""
    __tablename__ = "skill_tree_templates"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
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
    """Skill Node - a single skill within a template
    
    NOTE: Matches database_schema.sql - does NOT have node_type or keywords columns
    """
    __tablename__ = "template_skill_nodes"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skill_tree_templates.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    color: Mapped[Optional[str]] = mapped_column(String(20))
    difficulty_level: Mapped[Optional[str]] = mapped_column(String(20))  # beginner, intermediate, advanced, expert
    estimated_hours: Mapped[Optional[int]] = mapped_column(Integer)
    position_x: Mapped[Optional[int]] = mapped_column(Integer)
    position_y: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    template: Mapped["SkillTreeTemplateModel"] = relationship(back_populates="nodes")
    resources: Mapped[List["LearningResourceModel"]] = relationship(back_populates="skill_node")


class TemplateSkillPathModel(Base):
    """Closure table for template skill tree hierarchy"""
    __tablename__ = "template_skill_paths"
    
    ancestor_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    descendant_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


class LearningResourceModel(Base):
    """Learning Resource - materials linked to a skill node"""
    __tablename__ = "learning_resources"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_node_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("template_skill_nodes.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))  # video, article, course, book, tutorial, documentation
    platform: Mapped[Optional[str]] = mapped_column(String(100))
    estimated_duration: Mapped[Optional[int]] = mapped_column(Integer)  # minutes
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    skill_node: Mapped["TemplateSkillNodeModel"] = relationship(back_populates="resources")
