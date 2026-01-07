# Domain Ports (Interfaces)
# Following Hexagonal Architecture - Domain only knows interfaces, not implementations

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.entities import (
    User, ChatSession, Message, 
    SkillTreeTemplate, SkillNode, UserSkillTree, UserSkillNode, SkillTreePath,
    LearningResource, LearningProgress, StudySession, TimelineItem, Reminder,
    ForumCategory, ForumPost, ForumComment,
    Job
)


# ============================================================
# LLM PORT (for AI generation)
# ============================================================

class LLMPort(ABC):
    """Interface for Language Model interactions"""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str):
        """Generate text as stream"""
        pass


# ============================================================
# VECTOR STORE PORT (for RAG)
# ============================================================

class VectorStorePort(ABC):
    """Interface for Vector Database operations"""
    
    @abstractmethod
    def search(self, query: str, n_results: int = 3) -> List[str]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add documents to vector store"""
        pass


# ============================================================
# EMBEDDING PORT
# ============================================================

class EmbeddingPort(ABC):
    """Interface for text embedding"""
    
    @abstractmethod
    def encode(self, text: str) -> List[float]:
        """Encode text to vector"""
        pass
    
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts to vectors"""
        pass


# ============================================================
# USER REPOSITORY PORT
# ============================================================

class UserRepositoryPort(ABC):
    """Interface for User data access"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass
    
    @abstractmethod
    async def create(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        pass


# ============================================================
# CHAT REPOSITORY PORT
# ============================================================

class ChatRepositoryPort(ABC):
    """Interface for Chat data access"""
    
    @abstractmethod
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        pass
    
    @abstractmethod
    async def get_user_sessions(self, user_id: UUID) -> List[ChatSession]:
        pass
    
    @abstractmethod
    async def create_session(self, session: ChatSession) -> ChatSession:
        pass
    
    @abstractmethod
    async def add_message(self, message: Message) -> Message:
        pass
    
    @abstractmethod
    async def get_session_messages(self, session_id: UUID, limit: int = 50) -> List[Message]:
        pass


# ============================================================
# SKILL TREE REPOSITORY PORT
# ============================================================

class SkillTreeRepositoryPort(ABC):
    """Interface for Skill Tree data access"""
    
    # Template operations
    @abstractmethod
    async def get_all_templates(self) -> List[SkillTreeTemplate]:
        pass
    
    @abstractmethod
    async def get_template(self, template_id: UUID) -> Optional[SkillTreeTemplate]:
        pass
    
    @abstractmethod
    async def get_template_nodes(self, template_id: UUID) -> List[SkillNode]:
        pass
    
    @abstractmethod
    async def get_node_children(self, node_id: UUID) -> List[SkillNode]:
        """Get direct children of a node"""
        pass
    
    @abstractmethod
    async def get_node_descendants(self, node_id: UUID) -> List[SkillNode]:
        """Get all descendants of a node (using closure table)"""
        pass
    
    @abstractmethod
    async def get_node_ancestors(self, node_id: UUID) -> List[SkillNode]:
        """Get all ancestors of a node (path to root)"""
        pass
    
    # User tree operations
    @abstractmethod
    async def get_user_trees(self, user_id: UUID) -> List[UserSkillTree]:
        pass
    
    @abstractmethod
    async def get_user_tree(self, tree_id: UUID) -> Optional[UserSkillTree]:
        pass
    
    @abstractmethod
    async def create_user_tree(self, tree: UserSkillTree) -> UserSkillTree:
        pass
    
    @abstractmethod
    async def clone_template_to_user(self, template_id: UUID, user_id: UUID) -> UserSkillTree:
        """Clone a template to create user's personal tree"""
        pass
    
    @abstractmethod
    async def update_user_node(self, node: UserSkillNode) -> UserSkillNode:
        pass


# ============================================================
# LEARNING REPOSITORY PORT
# ============================================================

class LearningRepositoryPort(ABC):
    """Interface for Learning data access"""
    
    @abstractmethod
    async def get_resources_for_skill(self, skill_node_id: UUID) -> List[LearningResource]:
        pass
    
    @abstractmethod
    async def get_user_progress(self, user_id: UUID) -> List[LearningProgress]:
        pass
    
    @abstractmethod
    async def get_progress_for_resource(self, user_id: UUID, resource_id: UUID) -> Optional[LearningProgress]:
        pass
    
    @abstractmethod
    async def update_progress(self, progress: LearningProgress) -> LearningProgress:
        pass
    
    @abstractmethod
    async def create_study_session(self, session: StudySession) -> StudySession:
        pass
    
    @abstractmethod
    async def end_study_session(self, session_id: UUID) -> StudySession:
        pass
    
    @abstractmethod
    async def get_user_timeline(self, user_id: UUID) -> List[TimelineItem]:
        pass
    
    @abstractmethod
    async def add_to_timeline(self, item: TimelineItem) -> TimelineItem:
        pass
    
    @abstractmethod
    async def get_user_reminders(self, user_id: UUID) -> List[Reminder]:
        pass
    
    @abstractmethod
    async def create_reminder(self, reminder: Reminder) -> Reminder:
        pass


# ============================================================
# FORUM REPOSITORY PORT
# ============================================================

class ForumRepositoryPort(ABC):
    """Interface for Forum data access"""
    
    @abstractmethod
    async def get_categories(self) -> List[ForumCategory]:
        pass
    
    @abstractmethod
    async def get_posts(self, category_id: Optional[UUID] = None, limit: int = 20, offset: int = 0) -> List[ForumPost]:
        pass
    
    @abstractmethod
    async def get_post(self, post_id: UUID) -> Optional[ForumPost]:
        pass
    
    @abstractmethod
    async def create_post(self, post: ForumPost) -> ForumPost:
        pass
    
    @abstractmethod
    async def get_comments(self, post_id: UUID) -> List[ForumComment]:
        pass
    
    @abstractmethod
    async def create_comment(self, comment: ForumComment) -> ForumComment:
        pass
    
    @abstractmethod
    async def like_post(self, user_id: UUID, post_id: UUID) -> bool:
        pass
    
    @abstractmethod
    async def unlike_post(self, user_id: UUID, post_id: UUID) -> bool:
        pass


# ============================================================
# JOB REPOSITORY PORT
# ============================================================

class JobRepositoryPort(ABC):
    """Interface for Job data access"""
    
    @abstractmethod
    async def get_jobs(self, limit: int = 20, offset: int = 0) -> List[Job]:
        pass
    
    @abstractmethod
    async def get_job(self, job_id: UUID) -> Optional[Job]:
        pass
    
    @abstractmethod
    async def get_recommended_jobs(self, user_id: UUID) -> List[Job]:
        """Get jobs matching user's skills"""
        pass
    
    @abstractmethod
    async def search_jobs(self, query: str) -> List[Job]:
        pass
