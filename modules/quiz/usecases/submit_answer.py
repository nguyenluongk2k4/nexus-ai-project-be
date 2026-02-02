"""
Submit Answer Use Case
Handles submitting and validating a quiz answer
"""

from typing import Dict, Any, Optional
from uuid import UUID

from modules.quiz.domain.services.quiz_service import QuizService


class SubmitAnswerUseCase:
    """Use case for submitting an answer"""
    
    def __init__(self, quiz_service: QuizService):
        self.quiz_service = quiz_service
    
    async def execute(
        self,
        question_id: UUID,
        selected_index: int,
        time_taken_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute the submit answer use case
        
        Args:
            question_id: The question ID
            selected_index: Index of the selected option (0-3)
            time_taken_seconds: Time taken to answer in seconds
            
        Returns:
            Dict containing is_correct, explanation, etc.
        """
        return await self.quiz_service.submit_answer(
            question_id=question_id,
            selected_index=selected_index,
            time_taken_seconds=time_taken_seconds
        )
