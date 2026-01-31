"""
Complete Quiz Use Case
Handles completing a quiz and calculating final score
"""

from typing import Dict, Any
from uuid import UUID

from modules.quiz.domain.services.quiz_service import QuizService


class CompleteQuizUseCase:
    """Use case for completing a quiz"""
    
    def __init__(self, quiz_service: QuizService):
        self.quiz_service = quiz_service
    
    async def execute(self, attempt_id: UUID) -> Dict[str, Any]:
        """
        Execute the complete quiz use case
        
        Args:
            attempt_id: The quiz attempt ID
            
        Returns:
            Dict containing score, topic breakdown, and pass status
        """
        return await self.quiz_service.complete_quiz(attempt_id)
