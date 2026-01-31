"""
Quiz Repository - Database operations implementation
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from shared.database import get_db_context
from modules.quiz.domain.ports import QuizRepositoryPort, QuestionData, WeaknessAnalysis
from modules.quiz.infrastructure.models import QuizAttempt, QuizQuestion, QuizAnswer


class QuizRepositoryImpl(QuizRepositoryPort):
    """Implementation of quiz repository using SQLAlchemy"""
    
    async def create_attempt(
        self, 
        user_id: UUID, 
        node_id: UUID, 
        config_snapshot: Optional[Dict] = None
    ) -> QuizAttempt:
        async with get_db_context() as db:
            attempt = QuizAttempt(
                user_id=user_id,
                node_id=node_id,
                status="generating",
                config_snapshot=config_snapshot,
                started_at=datetime.utcnow()
            )
            db.add(attempt)
            await db.flush()
            await db.refresh(attempt)
            return attempt
    
    async def get_attempt(self, attempt_id: UUID) -> Optional[QuizAttempt]:
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizAttempt)
                .options(selectinload(QuizAttempt.questions).selectinload(QuizQuestion.user_answer))
                .where(QuizAttempt.id == attempt_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_attempts(self, user_id: UUID, node_id: UUID) -> List[QuizAttempt]:
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .where(QuizAttempt.node_id == node_id)
                .order_by(QuizAttempt.started_at.desc())
            )
            return list(result.scalars().all())
    
    async def update_attempt_status(
        self, 
        attempt_id: UUID, 
        status: str,
        score: Optional[float] = None,
        correct_count: Optional[int] = None
    ) -> bool:
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizAttempt).where(QuizAttempt.id == attempt_id)
            )
            attempt = result.scalar_one_or_none()
            if not attempt:
                return False
            
            attempt.status = status
            if score is not None:
                attempt.score = score
            if correct_count is not None:
                attempt.correct_count = correct_count
            if status == "completed":
                attempt.completed_at = datetime.utcnow()
            
            await db.flush()
            return True
    
    async def add_questions(
        self, 
        attempt_id: UUID, 
        questions: List[QuestionData]
    ) -> List[QuizQuestion]:
        async with get_db_context() as db:
            db_questions = []
            for idx, q in enumerate(questions):
                question = QuizQuestion(
                    attempt_id=attempt_id,
                    order_index=idx + 1,
                    content=q.content,
                    options=q.options,
                    correct_option_index=q.correct_option_index,
                    explanation=q.explanation,
                    topic_tag=q.topic_tag,
                    source_resource_id=UUID(q.source_resource_id) if q.source_resource_id else None,
                    source_resource_title=q.source_resource_title
                )
                db.add(question)
                db_questions.append(question)
            
            # Update attempt total questions
            result = await db.execute(
                select(QuizAttempt).where(QuizAttempt.id == attempt_id)
            )
            attempt = result.scalar_one_or_none()
            if attempt:
                attempt.total_questions = len(questions)
                attempt.status = "ready"
            
            await db.flush()
            for q in db_questions:
                await db.refresh(q)
            return db_questions
    
    async def get_questions(self, attempt_id: UUID) -> List[QuizQuestion]:
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizQuestion)
                .options(selectinload(QuizQuestion.user_answer))
                .where(QuizQuestion.attempt_id == attempt_id)
                .order_by(QuizQuestion.order_index)
            )
            return list(result.scalars().all())
    
    async def save_answer(
        self,
        question_id: UUID,
        selected_index: int,
        is_correct: bool,
        time_taken_seconds: Optional[int] = None
    ) -> QuizAnswer:
        async with get_db_context() as db:
            # Check if answer already exists
            existing = await db.execute(
                select(QuizAnswer).where(QuizAnswer.question_id == question_id)
            )
            answer = existing.scalar_one_or_none()
            
            if answer:
                # Update existing
                answer.selected_option_index = selected_index
                answer.is_correct = is_correct
                answer.time_taken_seconds = time_taken_seconds
                answer.answered_at = datetime.utcnow()
            else:
                # Create new
                answer = QuizAnswer(
                    question_id=question_id,
                    selected_option_index=selected_index,
                    is_correct=is_correct,
                    time_taken_seconds=time_taken_seconds
                )
                db.add(answer)
            
            await db.flush()
            await db.refresh(answer)
            return answer
    
    async def analyze_user_weakness(
        self, 
        user_id: UUID, 
        node_id: UUID
    ) -> WeaknessAnalysis:
        """Analyze user's weak topics based on historical quiz answers"""
        async with get_db_context() as db:
            # Get all attempts for this user on this node
            attempts_result = await db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .where(QuizAttempt.node_id == node_id)
                .where(QuizAttempt.status == "completed")
            )
            attempts = list(attempts_result.scalars().all())
            
            if not attempts:
                return WeaknessAnalysis(
                    weak_topics=[],
                    topic_error_counts={},
                    total_attempts=0,
                    total_wrong=0,
                    recommended_focus=[]
                )
            
            attempt_ids = [a.id for a in attempts]
            
            # Get all wrong answers with their topic tags
            questions_result = await db.execute(
                select(QuizQuestion)
                .options(selectinload(QuizQuestion.user_answer))
                .where(QuizQuestion.attempt_id.in_(attempt_ids))
            )
            questions = list(questions_result.scalars().all())
            
            # Count errors by topic
            topic_errors: Dict[str, int] = {}
            total_wrong = 0
            
            for q in questions:
                if q.user_answer and not q.user_answer.is_correct:
                    total_wrong += 1
                    tag = q.topic_tag or "general"
                    topic_errors[tag] = topic_errors.get(tag, 0) + 1
            
            # Sort topics by error count (descending)
            sorted_topics = sorted(topic_errors.items(), key=lambda x: x[1], reverse=True)
            weak_topics = [t[0] for t in sorted_topics]
            
            # Recommend top 3 weak topics for focus
            recommended = weak_topics[:3] if weak_topics else []
            
            return WeaknessAnalysis(
                weak_topics=weak_topics,
                topic_error_counts=topic_errors,
                total_attempts=len(attempts),
                total_wrong=total_wrong,
                recommended_focus=recommended
            )
    
    async def get_last_completed_attempt(
        self, 
        user_id: UUID, 
        node_id: UUID
    ) -> Optional[QuizAttempt]:
        """Get the most recent completed attempt for adaptive difficulty"""
        async with get_db_context() as db:
            result = await db.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .where(QuizAttempt.node_id == node_id)
                .where(QuizAttempt.status == "completed")
                .order_by(QuizAttempt.completed_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def get_user_all_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get all quiz stats for a user across all nodes for dashboard"""
        async with get_db_context() as db:
            # Get all completed attempts
            result = await db.execute(
                select(QuizAttempt)
                .options(selectinload(QuizAttempt.questions).selectinload(QuizQuestion.user_answer))
                .where(QuizAttempt.user_id == user_id)
                .where(QuizAttempt.status == "completed")
                .order_by(QuizAttempt.completed_at.desc())
            )
            attempts = list(result.scalars().all())
            
            if not attempts:
                return {
                    "total_quizzes_completed": 0,
                    "total_quizzes_passed": 0,
                    "average_score": 0.0,
                    "weak_topics": [],
                    "recommended_focus": [],
                    "recent_node_id": None,
                    "recent_node_name": None
                }
            
            # Calculate stats
            total_completed = len(attempts)
            total_passed = sum(1 for a in attempts if a.score and a.score >= 70)
            avg_score = sum(a.score or 0 for a in attempts) / total_completed if total_completed > 0 else 0
            
            # Aggregate weak topics across all attempts
            topic_errors: Dict[str, int] = {}
            for attempt in attempts:
                for q in attempt.questions:
                    if q.user_answer and not q.user_answer.is_correct:
                        tag = q.topic_tag or "general"
                        topic_errors[tag] = topic_errors.get(tag, 0) + 1
            
            sorted_topics = sorted(topic_errors.items(), key=lambda x: x[1], reverse=True)
            weak_topics = [t[0] for t in sorted_topics]
            recommended = weak_topics[:3] if weak_topics else []
            
            # Get most recent attempt's node info
            recent = attempts[0] if attempts else None
            
            return {
                "total_quizzes_completed": total_completed,
                "total_quizzes_passed": total_passed,
                "average_score": round(avg_score, 1),
                "weak_topics": weak_topics,
                "recommended_focus": recommended,
                "recent_node_id": str(recent.node_id) if recent else None,
                "recent_node_name": None  # Would need join to get node name
            }


def get_quiz_repository() -> QuizRepositoryImpl:
    """Factory function to get quiz repository instance"""
    return QuizRepositoryImpl()
