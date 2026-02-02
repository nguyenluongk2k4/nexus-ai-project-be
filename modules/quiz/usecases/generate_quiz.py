"""
Generate Quiz Use Case
Handles the flow of generating a personalized quiz for a user
"""

from typing import Dict, Any, List, Optional
from uuid import UUID

from modules.quiz.domain.services.quiz_service import QuizService


class GenerateQuizUseCase:
    """Use case for generating a personalized quiz"""
    
    def __init__(self, quiz_service: QuizService):
        self.quiz_service = quiz_service
    
    async def execute(
        self,
        user_id: UUID,
        node_id: UUID,
        node_name: str,
        node_description: str = "",
        num_questions: int = 5,
        resources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute the generate quiz use case
        
        Args:
            user_id: The user's ID
            node_id: The skill node ID to generate quiz for
            node_name: Name of the skill node
            node_description: Description of the skill node
            num_questions: Number of questions to generate
            resources: Optional list of learning resources for the node
            
        Returns:
            Dict containing attempt_id, status, and quiz info
        """
        return await self.quiz_service.generate_personalized_quiz(
            user_id=user_id,
            node_id=node_id,
            node_name=node_name,
            node_description=node_description,
            num_questions=num_questions,
            resources=resources
        )
