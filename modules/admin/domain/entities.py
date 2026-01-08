# Admin Module - Domain Entities
# SkillTree, SkillNode, LearningResource entities

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum


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


class ResourceType(str, Enum):
    VIDEO = "video"
    ARTICLE = "article"
    COURSE = "course"
    BOOK = "book"
    TUTORIAL = "tutorial"
    DOCUMENTATION = "documentation"


@dataclass
class SkillNode:
    """A node in the skill tree template"""
    id: UUID = field(default_factory=uuid4)
    template_id: Optional[UUID] = None
    name: str = ""
    description: Optional[str] = None
    node_type: NodeType = NodeType.KNOWLEDGE
    icon: Optional[str] = None
    color: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    estimated_hours: Optional[int] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SkillTreeTemplate:
    """A skill tree template created by admin"""
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
class LearningResource:
    """A learning resource attached to a skill node"""
    id: UUID = field(default_factory=uuid4)
    skill_node_id: UUID = field(default_factory=uuid4)
    title: str = ""
    url: Optional[str] = None
    resource_type: ResourceType = ResourceType.ARTICLE
    platform: Optional[str] = None
    estimated_duration: Optional[int] = None
    is_free: bool = True
    sort_order: int = 0


@dataclass
class SkillTreePath:
    """Closure table for skill tree hierarchy"""
    ancestor_id: UUID = field(default_factory=uuid4)
    descendant_id: UUID = field(default_factory=uuid4)
    depth: int = 0
