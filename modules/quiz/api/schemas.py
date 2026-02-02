"""
Quiz API Schemas - Pydantic models for request/response
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID


# ============ Request Schemas ============

class GenerateQuizRequest(BaseModel):
    """Request to generate a new quiz"""
    node_id: str
    node_name: str
    node_description: Optional[str] = ""
    num_questions: Optional[int] = 5


class SubmitAnswerRequest(BaseModel):
    """Request to submit an answer"""
    question_id: str
    selected_index: int
    time_taken_seconds: Optional[int] = None


# ============ Response Schemas ============

class QuestionResponse(BaseModel):
    """Quiz question response"""
    id: str
    order_index: int
    content: str
    options: List[str]
    topic_tag: Optional[str] = None
    # Review mode fields (only populated for completed quizzes)
    correct_option_index: Optional[int] = None
    explanation: Optional[str] = None
    user_selected_index: Optional[int] = None
    is_correct: Optional[bool] = None
    source_resource_id: Optional[str] = None
    source_resource_title: Optional[str] = None


class QuestionWithAnswerResponse(BaseModel):
    """Quiz question response with answer (after submission)"""
    id: str
    order_index: int
    content: str
    options: List[str]
    topic_tag: Optional[str] = None
    correct_option_index: int
    explanation: Optional[str] = None
    user_selected_index: Optional[int] = None
    is_correct: Optional[bool] = None


class GenerateQuizResponse(BaseModel):
    """Response after generating a quiz"""
    attempt_id: str
    status: str
    total_questions: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    message: str


class QuizDetailResponse(BaseModel):
    """Full quiz details"""
    attempt_id: str
    status: str
    score: Optional[float] = None
    correct_count: Optional[int] = None
    total_questions: int
    questions: List[QuestionResponse]
    config: Optional[Dict[str, Any]] = None


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer"""
    is_correct: bool
    correct_option_index: int
    explanation: Optional[str] = None
    selected_index: int


class CompleteQuizResponse(BaseModel):
    """Response after completing a quiz"""
    status: str
    score: float
    correct_count: int
    total_questions: int
    topic_breakdown: Dict[str, Dict[str, int]]
    passed: bool


class QuizHistoryItem(BaseModel):
    """Single quiz history item"""
    attempt_id: str
    status: str
    score: Optional[float] = None
    total_questions: int
    started_at: str
    completed_at: Optional[str] = None


class QuizHistoryResponse(BaseModel):
    """Quiz history for a node"""
    node_id: str
    attempts: List[QuizHistoryItem]
    weakness_analysis: Optional[Dict[str, Any]] = None


class UserQuizStatsResponse(BaseModel):
    """User's overall quiz statistics for dashboard"""
    total_quizzes_completed: int
    total_quizzes_passed: int
    average_score: float
    weak_topics: List[str]
    recommended_focus: List[str]
    recent_node_id: Optional[str] = None
    recent_node_name: Optional[str] = None
