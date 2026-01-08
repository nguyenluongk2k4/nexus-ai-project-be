# Admin Module - API Schemas

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


# Skill Tree Template Schemas
class SkillTreeTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class SkillTreeTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


# Skill Node Schemas
class SkillNodeCreate(BaseModel):
    template_id: str
    parent_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    node_type: str = "knowledge"
    icon: Optional[str] = None
    color: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_hours: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    keywords: Optional[List[str]] = None


class SkillNodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    node_type: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_hours: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    keywords: Optional[List[str]] = None


class SkillNodeResponse(BaseModel):
    id: str
    template_id: str
    name: str
    description: Optional[str] = None
    node_type: str
    icon: Optional[str] = None
    color: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_hours: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    keywords: Optional[List[str]] = None
    created_at: datetime


# Learning Resource Schemas
class LearningResourceCreate(BaseModel):
    skill_node_id: str
    title: str
    url: Optional[str] = None
    resource_type: str = "article"
    platform: Optional[str] = None
    estimated_duration: Optional[int] = None
    is_free: bool = True
    sort_order: int = 0


class LearningResourceResponse(BaseModel):
    id: str
    skill_node_id: str
    title: str
    url: Optional[str] = None
    resource_type: str
    platform: Optional[str] = None
    estimated_duration: Optional[int] = None
    is_free: bool = True
    sort_order: int = 0


# Common Response Schemas
class SuccessResponse(BaseModel):
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
