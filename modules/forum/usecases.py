# Forum Use Cases
# Application layer orchestration

from typing import List, Optional
from uuid import UUID

from modules.forum.domain.entities import ContributorStats
from modules.forum.domain.services import ContributorService


class GetTopContributorsUseCase:
    """Get top contributors for monthly leaderboard"""
    
    def __init__(self, contributor_service: ContributorService):
        self.contributor_service = contributor_service
    
    async def execute(
        self,
        limit: int = 10,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> List[ContributorStats]:
        """
        Get top contributors for the specified month.
        If month/year not provided, uses current month.
        
        Returns list of ContributorStats sorted by total_points descending.
        """
        return await self.contributor_service.get_monthly_top_contributors(
            limit=limit,
            month=month,
            year=year
        )
