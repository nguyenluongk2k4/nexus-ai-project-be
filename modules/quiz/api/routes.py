"""
Quiz API Routes - REST endpoints for quiz operations
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from modules.auth.api.deps import get_current_user_id
from modules.quiz.api.schemas import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    QuizDetailResponse,
    QuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    CompleteQuizResponse,
    QuizHistoryResponse,
    QuizHistoryItem,
    UserQuizStatsResponse
)
from modules.quiz.api.deps import (
    get_generate_quiz_usecase,
    get_submit_answer_usecase,
    get_complete_quiz_usecase,
    get_quiz_repo
)
from modules.quiz.usecases.generate_quiz import GenerateQuizUseCase
from modules.quiz.usecases.submit_answer import SubmitAnswerUseCase
from modules.quiz.usecases.complete_quiz import CompleteQuizUseCase


router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.get("/user-stats", response_model=UserQuizStatsResponse)
async def get_user_quiz_stats(
    user_id: UUID = Depends(get_current_user_id),
    repo = Depends(get_quiz_repo)
):
    """
    Get overall quiz statistics for the current user (for dashboard).
    Returns total quizzes, average score, weak topics, etc.
    """
    try:
        stats = await repo.get_user_all_stats(user_id)
        return UserQuizStatsResponse(**stats)
    except Exception as e:
        print(f"⚠️ Error getting user stats: {e}")
        return UserQuizStatsResponse(
            total_quizzes_completed=0,
            total_quizzes_passed=0,
            average_score=0.0,
            weak_topics=[],
            recommended_focus=[]
        )


@router.post("/generate", response_model=GenerateQuizResponse)
async def generate_quiz(
    request: GenerateQuizRequest,
    user_id: UUID = Depends(get_current_user_id),
    usecase: GenerateQuizUseCase = Depends(get_generate_quiz_usecase)
):
    """
    Generate a new personalized quiz for a skill node.
    AI will analyze user's historical performance and focus on weak topics.
    """
    try:
        # Fetch node resources for suggested resources feature
        resources = None
        try:
            from modules.skill_tree.infrastructure.repository import get_user_tree_repository
            tree_repo = get_user_tree_repository()
            node_resources = await tree_repo.get_node_resources(UUID(request.node_id))
            if node_resources:
                resources = [
                    {"id": str(r.id), "title": r.title, "description": r.description or ""}
                    for r in node_resources
                ]
        except Exception as res_err:
            print(f"⚠️ Could not fetch resources (non-fatal): {res_err}")
        
        result = await usecase.execute(
            user_id=user_id,
            node_id=UUID(request.node_id),
            node_name=request.node_name,
            node_description=request.node_description or "",
            num_questions=request.num_questions or 5,
            resources=resources
        )
        return GenerateQuizResponse(**result)
    except Exception as e:
        print(f"⚠️ Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


@router.get("/{attempt_id}", response_model=QuizDetailResponse)
async def get_quiz(
    attempt_id: str,
    user_id: UUID = Depends(get_current_user_id),
    repo = Depends(get_quiz_repo)
):
    """
    Get quiz details including questions.
    If quiz is completed, returns full answers for review.
    """
    attempt = await repo.get_attempt(UUID(attempt_id))
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this quiz")
    
    # If completed, include answers for review mode
    is_completed = attempt.status == "completed"
    
    questions = []
    for q in sorted(attempt.questions, key=lambda x: x.order_index):
        question_data = {
            "id": str(q.id),
            "order_index": q.order_index,
            "content": q.content,
            "options": q.options,
            "topic_tag": q.topic_tag
        }
        
        # Include answers and explanations for completed quizzes (review mode)
        if is_completed:
            question_data["correct_option_index"] = q.correct_option_index
            question_data["explanation"] = q.explanation
            question_data["source_resource_id"] = str(q.source_resource_id) if q.source_resource_id else None
            question_data["source_resource_title"] = q.source_resource_title
            
            # Include user's answer if exists
            if q.user_answer:
                question_data["user_selected_index"] = q.user_answer.selected_option_index
                question_data["is_correct"] = q.user_answer.is_correct
        
        questions.append(question_data)
    
    return QuizDetailResponse(
        attempt_id=str(attempt.id),
        status=attempt.status,
        score=attempt.score,
        correct_count=attempt.correct_count,
        total_questions=attempt.total_questions,
        questions=questions,
        config=attempt.config_snapshot
    )


@router.post("/{attempt_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    attempt_id: str,
    request: SubmitAnswerRequest,
    user_id: UUID = Depends(get_current_user_id),
    usecase: SubmitAnswerUseCase = Depends(get_submit_answer_usecase),
    repo = Depends(get_quiz_repo)
):
    """
    Submit an answer for a question.
    Returns whether the answer is correct and the explanation.
    """
    # Verify attempt belongs to user
    attempt = await repo.get_attempt(UUID(attempt_id))
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update attempt status to in_progress if needed
    if attempt.status == "ready":
        await repo.update_attempt_status(UUID(attempt_id), "in_progress")
    
    result = await usecase.execute(
        question_id=UUID(request.question_id),
        selected_index=request.selected_index,
        time_taken_seconds=request.time_taken_seconds
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return SubmitAnswerResponse(**result)


@router.post("/{attempt_id}/complete", response_model=CompleteQuizResponse)
async def complete_quiz(
    attempt_id: str,
    user_id: UUID = Depends(get_current_user_id),
    usecase: CompleteQuizUseCase = Depends(get_complete_quiz_usecase),
    repo = Depends(get_quiz_repo)
):
    """
    Complete the quiz and get final score with topic breakdown.
    """
    # Verify attempt belongs to user
    attempt = await repo.get_attempt(UUID(attempt_id))
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await usecase.execute(UUID(attempt_id))
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return CompleteQuizResponse(**result)


@router.get("/history/{node_id}", response_model=QuizHistoryResponse)
async def get_quiz_history(
    node_id: str,
    user_id: UUID = Depends(get_current_user_id),
    repo = Depends(get_quiz_repo)
):
    """
    Get quiz history for a specific node including weakness analysis.
    """
    attempts = await repo.get_user_attempts(user_id, UUID(node_id))
    weakness = await repo.analyze_user_weakness(user_id, UUID(node_id))
    
    history_items = [
        QuizHistoryItem(
            attempt_id=str(a.id),
            status=a.status,
            score=a.score,
            total_questions=a.total_questions,
            started_at=a.started_at.isoformat() if a.started_at else "",
            completed_at=a.completed_at.isoformat() if a.completed_at else None
        )
        for a in attempts
    ]
    
    return QuizHistoryResponse(
        node_id=node_id,
        attempts=history_items,
        weakness_analysis={
            "weak_topics": weakness.weak_topics,
            "topic_error_counts": weakness.topic_error_counts,
            "total_attempts": weakness.total_attempts,
            "total_wrong": weakness.total_wrong,
            "recommended_focus": weakness.recommended_focus
        } if weakness.total_attempts > 0 else None
    )
