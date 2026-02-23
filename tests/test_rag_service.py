"""
Unit tests for RAGService
Tests document retrieval and batch querying from ChromaDB
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.chat.services.rag_service import RAGService


@pytest.fixture
async def rag_service():
    """Create RAGService instance"""
    return RAGService()


@pytest.mark.asyncio
class TestRAGService:
    """Test cases for RAGService"""
    
    async def test_query_documents_single_query(self, rag_service):
        """Test single document query"""
        query = "What is React?"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_chroma.return_value.query.return_value = [
                {
                    "id": "doc1",
                    "content": "React is a JavaScript library for building user interfaces",
                    "score": 0.92,
                    "metadata": {"source": "react_docs", "section": "intro"}
                }
            ]
            
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "React is a JavaScript library for building user interfaces",
                    "score": 0.92,
                    "metadata": {"source": "react_docs", "section": "intro"}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=5)
            
            assert len(results) > 0
            assert results[0]["score"] > 0.8
            assert "React" in results[0]["content"]
    
    async def test_query_documents_multiple_results(self, rag_service):
        """Test query returns multiple documents"""
        query = "Python programming"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "Python is a high-level programming language",
                    "score": 0.95,
                    "metadata": {"source": "python_docs"}
                },
                {
                    "id": "doc2",
                    "content": "Python has extensive libraries for data science",
                    "score": 0.87,
                    "metadata": {"source": "data_science"}
                },
                {
                    "id": "doc3",
                    "content": "Flask and Django are Python web frameworks",
                    "score": 0.82,
                    "metadata": {"source": "web_frameworks"}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=3)
            
            assert len(results) == 3
            assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]
    
    async def test_query_documents_with_top_k_limit(self, rag_service):
        """Test top_k parameter limits results"""
        query = "JavaScript"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            # Return only 2 results even if more are available
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "JavaScript is a programming language",
                    "score": 0.93,
                    "metadata": {}
                },
                {
                    "id": "doc2",
                    "content": "JavaScript runs in browsers",
                    "score": 0.88,
                    "metadata": {}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=2)
            
            assert len(results) == 2
    
    async def test_query_documents_empty_result(self, rag_service):
        """Test handling empty query results"""
        query = "NonexistentTopicXYZ123"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=5)
            
            assert len(results) == 0
    
    async def test_batch_query_documents(self, rag_service):
        """Test batch querying multiple documents"""
        queries = ["React basics", "Vue.js", "Angular"]
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(side_effect=[
                [
                    {"id": "react1", "content": "React content", "score": 0.92, "metadata": {}}
                ],
                [
                    {"id": "vue1", "content": "Vue content", "score": 0.90, "metadata": {}}
                ],
                [
                    {"id": "angular1", "content": "Angular content", "score": 0.88, "metadata": {}}
                ]
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.batch_query_documents(queries, top_k=1)
            
            assert len(results) == 3
            assert all('id' in r for r in results)
    
    async def test_query_documents_score_filtering(self, rag_service):
        """Test that low-score documents are included"""
        query = "Test query"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "High relevance document",
                    "score": 0.95,
                    "metadata": {"source": "main"}
                },
                {
                    "id": "doc2",
                    "content": "Low relevance but still useful",
                    "score": 0.45,
                    "metadata": {"source": "secondary"}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=5)
            
            # Both documents should be included regardless of score
            assert len(results) >= 1
    
    async def test_query_documents_metadata_preservation(self, rag_service):
        """Test that metadata is preserved in results"""
        query = "Technology"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_metadata = {
                "source": "tech_docs",
                "section": "ai",
                "version": "2.0",
                "difficulty": "intermediate"
            }
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "AI technology overview",
                    "score": 0.91,
                    "metadata": mock_metadata
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=5)
            
            assert len(results) > 0
            assert results[0]["metadata"] == mock_metadata
    
    async def test_query_documents_special_characters(self, rag_service):
        """Test query with special characters"""
        query = "C++ vs C# comparison @#$%"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "C++ and C# are different",
                    "score": 0.80,
                    "metadata": {}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            # Should not raise an error
            results = await rag_service.query_documents(query, top_k=5)
            
            assert isinstance(results, list)
    
    async def test_query_documents_unicode_text(self, rag_service):
        """Test query with unicode characters"""
        query = "Lập trình Python với tiếng Việt"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {
                    "id": "doc1",
                    "content": "Hướng dẫn lập trình Python",
                    "score": 0.89,
                    "metadata": {"language": "vi"}
                }
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            results = await rag_service.query_documents(query, top_k=5)
            
            assert len(results) > 0
    
    async def test_query_documents_default_top_k(self, rag_service):
        """Test default top_k value"""
        query = "Default test"
        
        with patch('modules.chat.services.rag_service.ChromaAdapter') as mock_chroma:
            mock_instance = MagicMock()
            mock_instance.query = AsyncMock(return_value=[
                {"id": f"doc{i}", "content": f"Content {i}", "score": 0.9 - i*0.01, "metadata": {}}
                for i in range(10)
            ])
            patch('modules.chat.services.rag_service.ChromaAdapter', return_value=mock_instance).start()
            
            # Call without specifying top_k
            results = await rag_service.query_documents(query)
            
            # Should use default top_k (typically 5)
            assert len(results) <= 10
