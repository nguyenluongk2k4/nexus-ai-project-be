# API Schemas - Pydantic models for request/response
# Used by FastAPI for validation and Swagger documentation

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class NodeTypeEnum(str, Enum):
    SPECIALIZATION = "specialization"
    ABILITY = "ability"
    SKILL = "skill"
    KNOWLEDGE = "knowledge"


class DifficultyLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStatusEnum(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ResourceTypeEnum(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    COURSE = "course"
    BOOK = "book"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"


# ============================================================
# AUTH SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):
    """Request body for user registration"""
    email: str = Field(..., example="user@example.com")
    username: str = Field(..., min_length=3, max_length=50, example="johndoe")
    password: str = Field(..., min_length=6, example="securepassword123")
    full_name: Optional[str] = Field(None, example="John Doe")


class LoginRequest(BaseModel):
    """Request body for user login"""
    email: str = Field(..., example="user@example.com")
    password: str = Field(..., example="securepassword123")


class TokenResponse(BaseModel):
    """Response containing JWT token"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime


# ============================================================
# SKILL TREE SCHEMAS
# ============================================================

class SkillNodeCreate(BaseModel):
    """Request to create a new skill node"""
    name: str = Field(..., min_length=1, max_length=200, example="Docker Fundamentals")
    description: Optional[str] = Field(None, example="Learn containerization with Docker")
    node_type: NodeTypeEnum = Field(NodeTypeEnum.KNOWLEDGE, example="skill")
    difficulty_level: DifficultyLevelEnum = Field(DifficultyLevelEnum.BEGINNER, example="intermediate")
    estimated_hours: Optional[int] = Field(None, ge=1, example=20)
    keywords: Optional[List[str]] = Field(default_factory=list, example=["Docker", "Container", "DevOps"])
    position_x: Optional[int] = Field(None, example=100)
    position_y: Optional[int] = Field(None, example=200)
    parent_id: Optional[str] = Field(None, description="Parent node ID for tree hierarchy")


class SkillNodeUpdate(BaseModel):
    """Request to update a skill node"""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    node_type: Optional[NodeTypeEnum] = None
    difficulty_level: Optional[DifficultyLevelEnum] = None
    estimated_hours: Optional[int] = None
    keywords: Optional[List[str]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None


class SkillNodeResponse(BaseModel):
    """Skill node response"""
    id: str
    name: str
    description: Optional[str] = None
    node_type: str
    difficulty_level: str
    estimated_hours: Optional[int] = None
    keywords: List[str] = []
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    created_at: datetime


class SkillTreeTemplateCreate(BaseModel):
    """Request to create a skill tree template"""
    name: str = Field(..., example="Frontend Developer Roadmap")
    description: Optional[str] = Field(None, example="Complete roadmap for frontend development")
    category: Optional[str] = Field(None, example="Web Development")
    icon: Optional[str] = Field(None, example="💻")
    color: Optional[str] = Field(None, example="#3B82F6")


class SkillTreeTemplateResponse(BaseModel):
    """Skill tree template response"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    node_count: int = 0
    created_at: datetime


# ============================================================
# LEARNING RESOURCE SCHEMAS
# ============================================================

class LearningResourceCreate(BaseModel):
    """Request to create a learning resource"""
    skill_node_id: str = Field(..., description="ID of the skill node this resource belongs to")
    title: str = Field(..., example="Docker Official Documentation")
    url: Optional[str] = Field(None, example="https://docs.docker.com")
    resource_type: ResourceTypeEnum = Field(ResourceTypeEnum.DOCUMENTATION, example="documentation")
    platform: Optional[str] = Field(None, example="Docker")
    estimated_duration: Optional[int] = Field(None, ge=1, description="Duration in minutes", example=60)
    is_free: bool = Field(True, example=True)


class LearningResourceResponse(BaseModel):
    """Learning resource response"""
    id: str
    skill_node_id: str
    title: str
    url: Optional[str] = None
    resource_type: str
    platform: Optional[str] = None
    estimated_duration: Optional[int] = None
    is_free: bool = True


# ============================================================
# LEARNING PROGRESS SCHEMAS
# ============================================================

class ProgressUpdateRequest(BaseModel):
    """Request to update learning progress"""
    status: LearningStatusEnum = Field(..., example="in_progress")
    progress_percent: Optional[int] = Field(None, ge=0, le=100, example=50)
    notes: Optional[str] = Field(None, example="Completed chapter 1")
    rating: Optional[int] = Field(None, ge=1, le=5, example=4)


class LearningProgressResponse(BaseModel):
    """Learning progress response"""
    id: str
    user_id: str
    resource_id: str
    status: str
    progress_percent: int
    notes: Optional[str] = None
    rating: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LearningStatsResponse(BaseModel):
    """Learning statistics response"""
    total_nodes: int
    completed: int
    in_progress: int
    not_started: int
    completion_percent: float


# ============================================================
# CHAT SCHEMAS
# ============================================================

class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    text: str = Field(..., min_length=1, example="Làm sao để học Docker?")
    session_id: Optional[str] = Field(None, description="Existing session ID or null for new session")


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    session_id: str
    user_message: str
    bot_response: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """Chat session response"""
    id: str
    title: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


# ============================================================
# COMMON SCHEMAS
# ============================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str = "Success"
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    details: Optional[dict] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
