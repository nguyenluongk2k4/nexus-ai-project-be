# Forum Module - Providers (Dependency Injection)

from sqlalchemy.ext.asyncio import AsyncSession

from modules.forum.infrastructure.repository import ForumRepositoryImpl


def get_forum_repository(session: AsyncSession) -> ForumRepositoryImpl:
    """Get forum repository instance"""
    return ForumRepositoryImpl(session)
