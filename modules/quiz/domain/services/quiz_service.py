"""
Quiz Domain Service - Business logic for personalized quiz generation
"""

from typing import Optional, Dict, Any, List
from uuid import UUID

from modules.quiz.domain.ports import QuizRepositoryPort, QuizGeneratorPort, WeaknessAnalysis, QuestionData


class QuizService:
    """Domain service for quiz operations"""
    
    def __init__(
        self, 
        repository: QuizRepositoryPort, 
        generator: QuizGeneratorPort
    ):
        self.repository = repository
        self.generator = generator
    
    async def analyze_user_weakness(
        self, 
        user_id: UUID, 
        node_id: UUID
    ) -> WeaknessAnalysis:
        """Analyze user's weak topics based on historical quiz performance"""
        return await self.repository.analyze_user_weakness(user_id, node_id)
    
    async def generate_personalized_quiz(
        self,
        user_id: UUID,
        node_id: UUID,
        node_name: str,
        node_description: str,
        num_questions: int = 5,
        resources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized quiz for the user.
        Uses historical data to focus on weak topics.
        """
        # Step 1: Analyze user's weaknesses
        weakness = await self.analyze_user_weakness(user_id, node_id)
        
        # Step 2: Adaptive Difficulty based on last attempt
        last_attempt = await self.repository.get_last_completed_attempt(user_id, node_id)
        
        if last_attempt and last_attempt.score is not None:
            if last_attempt.score < 40:
                difficulty = "easy"
            elif last_attempt.score < 70:
                difficulty = "medium"
            else:  # Score >= 70, user passed before
                difficulty = "hard"
        else:
            # First attempt - default to medium
            difficulty = "medium"
        
        # Focus on weak topics
        focus_topics = weakness.recommended_focus
        
        config_snapshot = {
            "focus_topics": focus_topics,
            "difficulty": difficulty,
            "weakness_analysis": {
                "total_attempts": weakness.total_attempts,
                "total_wrong": weakness.total_wrong,
                "topic_error_counts": weakness.topic_error_counts
            },
            "last_score": last_attempt.score if last_attempt else None
        }
        
        # Step 3: Create quiz attempt
        attempt = await self.repository.create_attempt(
            user_id=user_id,
            node_id=node_id,
            config_snapshot=config_snapshot
        )
        
        # Step 4: Generate questions using AI
        questions = await self.generator.generate_questions(
            node_name=node_name,
            node_description=node_description or f"Kiến thức về {node_name}",
            num_questions=num_questions,
            focus_topics=focus_topics if focus_topics else None,
            difficulty=difficulty,
            resources=resources
        )
        
        if not questions:
            # Fallback: update status to error
            await self.repository.update_attempt_status(attempt.id, "error")
            return {
                "attempt_id": str(attempt.id),
                "status": "error",
                "message": "Không thể sinh câu hỏi. Vui lòng thử lại."
            }
        
        # Step 5: Save questions to database
        await self.repository.add_questions(attempt.id, questions)
        
        return {
            "attempt_id": str(attempt.id),
            "status": "ready",
            "total_questions": len(questions),
            "config": config_snapshot,
            "message": f"Quiz đã sẵn sàng với {len(questions)} câu hỏi"
        }
    
    async def submit_answer(
        self,
        question_id: UUID,
        selected_index: int,
        time_taken_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Submit an answer for a question"""
        # Get questions to find correct answer
        # Note: This is simplified - in production, you'd want to optimize this
        from modules.quiz.infrastructure.models import QuizQuestion
        from shared.database import get_db_context
        from sqlalchemy import select
        
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizQuestion).where(QuizQuestion.id == question_id)
            )
            question = result.scalar_one_or_none()
            
            if not question:
                return {"error": "Question not found"}
            
            is_correct = selected_index == question.correct_option_index
            
            # Save answer
            answer = await self.repository.save_answer(
                question_id=question_id,
                selected_index=selected_index,
                is_correct=is_correct,
                time_taken_seconds=time_taken_seconds
            )
            
            return {
                "is_correct": is_correct,
                "correct_option_index": question.correct_option_index,
                "explanation": question.explanation,
                "selected_index": selected_index
            }
    
    async def complete_quiz(self, attempt_id: UUID) -> Dict[str, Any]:
        """Complete a quiz and calculate final score"""
        # Get attempt with all questions and answers
        attempt = await self.repository.get_attempt(attempt_id)
        
        if not attempt:
            return {"error": "Attempt not found"}
        
        # Calculate score
        total_questions = len(attempt.questions)
        correct_count = sum(
            1 for q in attempt.questions 
            if q.user_answer and q.user_answer.is_correct
        )
        
        score = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Update attempt
        await self.repository.update_attempt_status(
            attempt_id=attempt_id,
            status="completed",
            score=score,
            correct_count=correct_count
        )
        
        # Analyze performance by topic
        topic_results: Dict[str, Dict[str, int]] = {}
        for q in attempt.questions:
            tag = q.topic_tag or "general"
            if tag not in topic_results:
                topic_results[tag] = {"correct": 0, "total": 0}
            topic_results[tag]["total"] += 1
            if q.user_answer and q.user_answer.is_correct:
                topic_results[tag]["correct"] += 1
        
        passed = score >= 70
        
        # Auto-complete the skill tree node if passed
        if passed:
            try:
                from shared.database import get_db_context
                from sqlalchemy import select
                from datetime import datetime
                from modules.skill_tree.infrastructure.models import (
                    UserSkillNodeModel, 
                    UserSkillTreeModel, 
                    LearningResourceModel,
                    LearningProgressModel
                )
                
                async with get_db_context() as db:
                    # Find the user node. attempt.node_id could be the User Node ID or Template ID
                    node_stmt = select(UserSkillNodeModel).where(
                        (UserSkillNodeModel.id == attempt.node_id) | 
                        (UserSkillNodeModel.original_node_id == attempt.node_id)
                    ).where(
                        UserSkillNodeModel.tree_id.in_(
                            select(UserSkillTreeModel.id).where(UserSkillTreeModel.user_id == attempt.user_id)
                        )
                    )
                    node_result = await db.execute(node_stmt)
                    user_node = node_result.scalar_one_or_none()
                    
                    if user_node and user_node.status != 'completed':
                        # Check resources
                        resources_stmt = select(LearningResourceModel.id).where(
                            LearningResourceModel.skill_node_id == user_node.original_node_id
                        )
                        resources_result = await db.execute(resources_stmt)
                        resource_ids = [r[0] for r in resources_result.fetchall()]
                        
                        if not resource_ids:
                            all_resources_completed = True
                        else:
                            # Check if all these resources have 'completed' status in LearningProgress for this user
                            progress_stmt = select(LearningProgressModel).where(
                                LearningProgressModel.user_id == attempt.user_id,
                                LearningProgressModel.resource_id.in_(resource_ids),
                                LearningProgressModel.status == 'completed'
                            )
                            progress_result = await db.execute(progress_stmt)
                            completed_resources = progress_result.scalars().all()
                            
                            all_resources_completed = len(completed_resources) == len(resource_ids)
                        
                        if all_resources_completed:
                            user_node.status = 'completed'
                            user_node.completed_at = datetime.now()
                            user_node.progress_percent = 100
                            await db.commit()
            except Exception as e:
                print(f"⚠️ Failed to auto-complete node after passing quiz: {e}")
        
        return {
            "status": "completed",
            "score": round(score, 1),
            "correct_count": correct_count,
            "total_questions": total_questions,
            "topic_breakdown": topic_results,
            "passed": passed
        }


def get_quiz_service() -> QuizService:
    """Factory function to get quiz service instance"""
    from modules.quiz.infrastructure.repository import get_quiz_repository
    from modules.quiz.infrastructure.quiz_generator import get_quiz_generator
    
    return QuizService(
        repository=get_quiz_repository(),
        generator=get_quiz_generator()
    )
