"""
Quiz API Dependencies - Dependency Injection
"""

from modules.quiz.domain.services.quiz_service import get_quiz_service, QuizService
from modules.quiz.usecases.generate_quiz import GenerateQuizUseCase
from modules.quiz.usecases.submit_answer import SubmitAnswerUseCase
from modules.quiz.usecases.complete_quiz import CompleteQuizUseCase
from modules.quiz.infrastructure.repository import get_quiz_repository


def get_generate_quiz_usecase() -> GenerateQuizUseCase:
    """Get GenerateQuizUseCase instance"""
    return GenerateQuizUseCase(get_quiz_service())


def get_submit_answer_usecase() -> SubmitAnswerUseCase:
    """Get SubmitAnswerUseCase instance"""
    return SubmitAnswerUseCase(get_quiz_service())


def get_complete_quiz_usecase() -> CompleteQuizUseCase:
    """Get CompleteQuizUseCase instance"""
    return CompleteQuizUseCase(get_quiz_service())


def get_quiz_repo():
    """Get quiz repository instance"""
    return get_quiz_repository()
