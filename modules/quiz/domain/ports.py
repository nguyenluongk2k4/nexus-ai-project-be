"""
Quiz Domain Ports - Interfaces for Quiz Operations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass


@dataclass
class QuestionData:
    """Data class for question from AI"""
    content: str
    options: List[str]
    correct_option_index: int
    explanation: str
    topic_tag: str
    source_resource_id: Optional[str] = None
    source_resource_title: Optional[str] = None


@dataclass
class WeaknessAnalysis:
    """Analysis of user's weak topics"""
    weak_topics: List[str]  # Topics user often gets wrong
    topic_error_counts: Dict[str, int]  # topic -> error count
    total_attempts: int
    total_wrong: int
    recommended_focus: List[str]  # Topics to focus on next quiz


class QuizRepositoryPort(ABC):
    """Interface for quiz data persistence"""
    
    @abstractmethod
    async def create_attempt(
        self, 
        user_id: UUID, 
        node_id: UUID, 
        config_snapshot: Optional[Dict] = None
    ) -> Any:
        """Create a new quiz attempt"""
        pass
    
    @abstractmethod
    async def get_attempt(self, attempt_id: UUID) -> Optional[Any]:
        """Get quiz attempt by ID"""
        pass
    
    @abstractmethod
    async def get_user_attempts(self, user_id: UUID, node_id: UUID) -> List[Any]:
        """Get all attempts for a user on a specific node"""
        pass
    
    @abstractmethod
    async def update_attempt_status(
        self, 
        attempt_id: UUID, 
        status: str,
        score: Optional[float] = None,
        correct_count: Optional[int] = None
    ) -> bool:
        """Update attempt status"""
        pass
    
    @abstractmethod
    async def add_questions(
        self, 
        attempt_id: UUID, 
        questions: List[QuestionData]
    ) -> List[Any]:
        """Add questions to an attempt"""
        pass
    
    @abstractmethod
    async def get_questions(self, attempt_id: UUID) -> List[Any]:
        """Get all questions for an attempt"""
        pass
    
    @abstractmethod
    async def save_answer(
        self,
        question_id: UUID,
        selected_index: int,
        is_correct: bool,
        time_taken_seconds: Optional[int] = None
    ) -> Any:
        """Save user's answer"""
        pass
    
    @abstractmethod
    async def analyze_user_weakness(
        self, 
        user_id: UUID, 
        node_id: UUID
    ) -> WeaknessAnalysis:
        """Analyze user's weak topics based on historical answers"""
        pass
    
    @abstractmethod
    async def get_last_completed_attempt(
        self, 
        user_id: UUID, 
        node_id: UUID
    ) -> Optional[Any]:
        """Get the most recent completed attempt for adaptive difficulty"""
        pass


class QuizGeneratorPort(ABC):
    """Interface for AI quiz generation"""
    
    @abstractmethod
    async def generate_questions(
        self,
        node_name: str,
        node_description: str,
        num_questions: int = 5,
        focus_topics: Optional[List[str]] = None,
        difficulty: str = "medium",
        resources: Optional[List[dict]] = None
    ) -> List[QuestionData]:
        """Generate quiz questions using AI"""
        pass
