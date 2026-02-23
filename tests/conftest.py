"""
Pytest configuration and shared fixtures for backend tests
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    # Use SQLite in-memory for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    from unittest.mock import AsyncMock, MagicMock
    
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.set = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_client.publish = AsyncMock()
    mock_client.subscribe = AsyncMock()
    mock_client.hset = AsyncMock()
    mock_client.hget = AsyncMock()
    
    return mock_client


@pytest.fixture
def mock_gemini_client():
    """Mock Google Gemini API client"""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = MagicMock()
    mock.generate_content = AsyncMock()
    return mock


@pytest.fixture
def mock_chroma_adapter():
    """Mock ChromaDB adapter"""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = MagicMock()
    mock.query = AsyncMock(return_value=[])
    mock.batch_query = AsyncMock(return_value=[])
    
    return mock
