# Domain Entities

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum


# ============================================================
# USER DOMAIN
# ============================================================

@dataclass
class User:
    """User entity - represents a registered user"""
    id: UUID = field(default_factory=uuid4)
    email: str = ""
    username: str = ""
    password_hash: str = ""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None


# ============================================================
# CHAT DOMAIN
# ============================================================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """A single message in a chat session"""
    id: UUID = field(default_factory=uuid4)
    session_id: UUID = field(default_factory=uuid4)
    role: MessageRole = MessageRole.USER
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    """A chat session between user and AI"""
    id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    title: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# ============================================================
# SKILL TREE DOMAIN
# ============================================================

class NodeType(str, Enum):
    SPECIALIZATION = "specialization"
    ABILITY = "ability"
    SKILL = "skill"
    KNOWLEDGE = "knowledge"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class SkillNode:
    """A node in the skill tree (template)"""
    id: UUID = field(default_factory=uuid4)
    template_id: Optional[UUID] = None
    name: str = ""
    description: Optional[str] = None
    node_type: NodeType = NodeType.KNOWLEDGE
    icon: Optional[str] = None
    color: Optional[str] = None
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER
    estimated_hours: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SkillTreeTemplate:
    """A skill tree template (created by admin)"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: bool = True
    nodes: List[SkillNode] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserSkillNode:
    """A node in user's personal skill tree"""
    id: UUID = field(default_factory=uuid4)
    tree_id: UUID = field(default_factory=uuid4)
    original_node_id: Optional[UUID] = None  # Link to template node
    name: str = ""
    description: Optional[str] = None
    status: LearningStatus = LearningStatus.NOT_STARTED
    progress_percent: int = 0
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserSkillTree:
    """User's personal skill tree (cloned from template or custom)"""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    template_id: Optional[UUID] = None  # NULL if custom created
    name: str = ""
    description: Optional[str] = None
    nodes: List[UserSkillNode] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SkillTreePath:
    """Closure table for skill tree hierarchy (ancestor-descendant relationship)"""
    ancestor_id: UUID = field(default_factory=uuid4)
    descendant_id: UUID = field(default_factory=uuid4)
    depth: int = 0


# ============================================================
# LEARNING DOMAIN
# ============================================================

class ResourceType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    COURSE = "course"
    BOOK = "book"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class LearningResource:
    """A learning resource attached to a skill node"""
    id: UUID = field(default_factory=uuid4)
    skill_node_id: UUID = field(default_factory=uuid4)
    title: str = ""
    url: Optional[str] = None
    resource_type: ResourceType = ResourceType.ARTICLE
    platform: Optional[str] = None
    estimated_duration: Optional[int] = None  # minutes
    is_free: bool = True
    sort_order: int = 0


@dataclass
class LearningProgress:
    """User's progress on a learning resource"""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    resource_id: UUID = field(default_factory=uuid4)
    status: LearningStatus = LearningStatus.NOT_STARTED
    progress_percent: int = 0
    notes: Optional[str] = None
    rating: Optional[int] = None  # 1-5
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class StudySession:
    """A study session for tracking time spent"""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    resource_id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class TimelineItem:
    """A scheduled learning item"""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    resource_id: UUID = field(default_factory=uuid4)
    scheduled_date: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Reminder:
    """A reminder for learning"""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    resource_id: Optional[UUID] = None
    reminder_at: datetime = field(default_factory=datetime.now)
    message: Optional[str] = None
    is_sent: bool = False
    created_at: datetime = field(default_factory=datetime.now)


# ============================================================
# FORUM DOMAIN
# ============================================================

@dataclass
class ForumCategory:
    """Forum category"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    description: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0


@dataclass
class ForumPost:
    """A forum post"""
    id: UUID = field(default_factory=uuid4)
    category_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    title: str = ""
    content: str = ""
    view_count: int = 0
    is_pinned: bool = False
    is_locked: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ForumComment:
    """A comment on a forum post"""
    id: UUID = field(default_factory=uuid4)
    post_id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None  # For nested comments
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# ============================================================
# JOB DOMAIN
# ============================================================

class JobType(str, Enum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


@dataclass
class Job:
    """A job listing"""
    id: UUID = field(default_factory=uuid4)
    title: str = ""
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: JobType = JobType.FULL_TIME
    experience_level: ExperienceLevel = ExperienceLevel.MID
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    description: Optional[str] = None
    requirements: Optional[str] = None
    benefits: Optional[str] = None
    apply_url: Optional[str] = None
    is_active: bool = True
    posted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
