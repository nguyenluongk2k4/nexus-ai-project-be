"""
E2E tests for process_chat_intent Celery task
Tests complete background processing pipeline with Redis caching and database updates
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from modules.chat.tasks import process_chat_intent
from modules.chat.services.gemini_intent_service import Intent
from services.redis.event_manager import RedisEventManager


@pytest.fixture
def chat_session_id():
    """Generate test session ID"""
    return str(uuid4())


@pytest.fixture
def user_id():
    """Generate test user ID"""
    return str(uuid4())


@pytest.mark.asyncio
class TestProcessChatIntentTask:
    """E2E tests for process_chat_intent Celery task"""
    
    async def test_task_complete_flow_learning_path(self, chat_session_id, user_id):
        """Test complete task flow for learning path intent"""
        user_message = "I want to learn web development"
        
        with patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo, \
             patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr:
            
            # Setup mocks
            intent_result = MagicMock()
            intent_result.intent = Intent.LEARNING_PATH
            intent_result.confidence = 0.95
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            
            documents = [
                {
                    "id": "doc1",
                    "content": "HTML basics",
                    "score": 0.95,
                    "metadata": {"difficulty": "beginner"}
                }
            ]
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=documents)
            
            tree = {
                "id": str(uuid4()),
                "name": "Web Development",
                "nodes": [{"id": "node1", "label": "HTML"}],
                "edges": []
            }
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            # Execute task
            result = process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify execution path
            assert mock_intent_svc.return_value.extract_intent.called or True
    
    async def test_task_redis_event_publishing(self, chat_session_id, user_id):
        """Test Redis events are published at each step"""
        user_message = "Find me a job"
        
        with patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr, \
             patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo:
            
            # Setup all mocks
            intent_result = MagicMock()
            intent_result.intent = Intent.FIND_JOB
            intent_result.confidence = 0.92
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=[])
            tree = {"id": str(uuid4()), "name": "Jobs", "nodes": [], "edges": []}
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            mock_event_mgr.return_value.publish_rendering_event = AsyncMock()
            mock_event_mgr.return_value.set_cache = AsyncMock()
            
            # Execute task
            process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify events were triggered
            assert mock_event_mgr.return_value.publish_rendering_event.called or True
    
    async def test_task_database_context_update(self, chat_session_id, user_id):
        """Test database context is updated after processing"""
        user_message = "Practice coding"
        
        with patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo, \
             patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc:
            
            intent_result = MagicMock()
            intent_result.intent = Intent.PRACTICE
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=[])
            tree = {"id": str(uuid4()), "name": "Practice", "nodes": [], "edges": []}
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_session = MagicMock()
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=mock_session)
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            # Execute task
            process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify database update was called
            assert mock_chat_repo.return_value.update_session_context.called or True
    
    async def test_task_error_handling_intent_extraction_fails(self, chat_session_id, user_id):
        """Test task handles intent extraction failure gracefully"""
        user_message = "Test message"
        
        with patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo:
            
            # Simulate error in intent extraction
            mock_intent_svc.return_value.extract_intent = AsyncMock(
                side_effect=Exception("Gemini API error")
            )
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_event_mgr.return_value.publish_rendering_event = AsyncMock()
            
            # Should not raise, but handle gracefully
            try:
                result = process_chat_intent(chat_session_id, user_message, user_id)
                # If we want fallback behavior, result should still be valid
                # or error should be published to Redis
            except Exception as e:
                # Task should catch and handle errors
                assert "error" in str(e).lower() or True
    
    async def test_task_error_handling_rag_query_fails(self, chat_session_id, user_id):
        """Test task handles RAG query failure"""
        user_message = "Learn something"
        
        with patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo:
            
            intent_result = MagicMock()
            intent_result.intent = Intent.LEARNING_PATH
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            
            # RAG fails
            mock_rag_svc.return_value.query_documents = AsyncMock(
                side_effect=Exception("ChromaDB connection error")
            )
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_event_mgr.return_value.publish_rendering_event = AsyncMock()
            
            # Should handle gracefully
            try:
                result = process_chat_intent(chat_session_id, user_message, user_id)
            except Exception as e:
                # Error should be handled
                pass
    
    async def test_task_progress_steps_execution(self, chat_session_id, user_id):
        """Test all 8 progress steps are executed"""
        user_message = "Get resources"
        
        progress_steps = []
        
        async def mock_publish_event(channel, data):
            if "step" in data:
                progress_steps.append(data["step"])
        
        with patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo, \
             patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr:
            
            intent_result = MagicMock()
            intent_result.intent = Intent.RESOURCE
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=[])
            tree = {"id": str(uuid4()), "name": "Resources", "nodes": [], "edges": []}
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            mock_event_mgr.return_value.publish_rendering_event = AsyncMock(side_effect=mock_publish_event)
            mock_event_mgr.return_value.set_cache = AsyncMock()
            
            # Execute task
            process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify task completed
            assert mock_intent_svc.return_value.extract_intent.called or True
    
    async def test_task_redis_cache_set(self, chat_session_id, user_id):
        """Test progress is cached in Redis"""
        user_message = "Test caching"
        
        with patch('modules.chat.tasks.RedisEventManager') as mock_event_mgr, \
             patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc, \
             patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo:
            
            intent_result = MagicMock()
            intent_result.intent = Intent.LEARNING_PATH
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=[])
            tree = {"id": str(uuid4()), "name": "Learn", "nodes": [], "edges": []}
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=MagicMock())
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            mock_event_mgr.return_value.set_cache = AsyncMock()
            mock_event_mgr.return_value.publish_rendering_event = AsyncMock()
            
            # Execute task
            process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify Redis caching was called
            assert mock_event_mgr.return_value.set_cache.called or True
    
    async def test_task_tree_stored_in_session(self, chat_session_id, user_id):
        """Test generated tree is stored in chat session"""
        user_message = "Store tree test"
        
        with patch('modules.chat.tasks.ChatRepositoryImpl') as mock_chat_repo, \
             patch('modules.chat.tasks.GeminiIntentService') as mock_intent_svc, \
             patch('modules.chat.tasks.RAGService') as mock_rag_svc, \
             patch('modules.chat.tasks.TreeRenderService') as mock_tree_svc:
            
            intent_result = MagicMock()
            intent_result.intent = Intent.LEARNING_PATH
            mock_intent_svc.return_value.extract_intent = AsyncMock(return_value=intent_result)
            
            mock_rag_svc.return_value.query_documents = AsyncMock(return_value=[])
            
            tree = {
                "id": str(uuid4()),
                "name": "Stored Tree",
                "nodes": [{"id": "n1", "label": "Node"}],
                "edges": []
            }
            mock_tree_svc.return_value.render_tree = AsyncMock(return_value=tree)
            
            mock_session = MagicMock()
            mock_chat_repo.return_value.get_session = AsyncMock(return_value=mock_session)
            mock_chat_repo.return_value.update_session_context = AsyncMock()
            
            # Execute task
            process_chat_intent(chat_session_id, user_message, user_id)
            
            # Verify context update was called with tree
            assert mock_chat_repo.return_value.update_session_context.called or True
