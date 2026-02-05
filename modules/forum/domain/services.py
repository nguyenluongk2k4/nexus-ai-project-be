# Forum Domain - Contributor Service
# Business logic for calculating contributor scores

from datetime import datetime
from typing import List

from modules.forum.domain.entities import ContributorStats
from modules.forum.domain.ports import ForumRepositoryPort


class ContributorService:
    """Service for contributor-related operations"""
    
    # Scoring constants
    POST_POINTS = 10
    COMMENT_POINTS = 2
    LIKE_POINTS = 5
    
    def __init__(self, repository: ForumRepositoryPort):
        self.repository = repository
    
    async def get_monthly_top_contributors(
        self, 
        limit: int = 10,
        month: int = None,
        year: int = None
    ) -> List[ContributorStats]:
        """
        Get top contributors for a specific month.
        If month/year not specified, use current month.
        
        Scoring:
        - Create Post: 10 points
        - Write Comment: 2 points
        - Receive Like: 5 points
        """
        # Default to current month/year if not specified
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year
        
        # Fetch from repository (repository handles all the DB logic)
        contributors = await self.repository.get_top_contributors(
            limit=limit,
            month=target_month,
            year=target_year
        )
        
        return contributors
