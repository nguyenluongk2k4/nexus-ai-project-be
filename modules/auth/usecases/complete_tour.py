# Auth Module - Complete Tour Use Case

from uuid import UUID
from modules.auth.domain.ports import AuthRepositoryPort


class CompleteTourUseCase:
    """Use case for completing the onboarding tour"""
    
    def __init__(self, user_repository: AuthRepositoryPort):
        self.user_repo = user_repository
    
    async def execute(self, user_id: UUID, phase: str = "all") -> None:
        """Mark a specific tour phase as completed for a user"""
        await self.user_repo.update_tour_status(user_id, True, phase)
