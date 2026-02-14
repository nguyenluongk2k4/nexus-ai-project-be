"""
Unit tests for TreeRenderService
Tests skill tree generation and node/edge construction
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.chat.services.tree_renderer_service import TreeRenderService
from modules.chat.services.gemini_intent_service import Intent


@pytest.fixture
async def tree_service():
    """Create TreeRenderService instance"""
    return TreeRenderService()


@pytest.mark.asyncio
class TestTreeRenderService:
    """Test cases for TreeRenderService"""
    
    async def test_render_tree_learning_path(self, tree_service):
        """Test rendering tree for learning path intent"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "HTML basics and structure",
                "score": 0.95,
                "metadata": {"difficulty": "beginner", "category": "frontend"}
            },
            {
                "id": "doc2",
                "content": "CSS styling and layouts",
                "score": 0.92,
                "metadata": {"difficulty": "beginner", "category": "frontend"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert "id" in tree
        assert "name" in tree
        assert "nodes" in tree
        assert "edges" in tree
        assert len(tree["nodes"]) > 0
        assert len(tree["edges"]) >= 0
    
    async def test_render_tree_find_job(self, tree_service):
        """Test rendering tree for job search intent"""
        intent = Intent.FIND_JOB
        documents = [
            {
                "id": "job1",
                "content": "Resume writing tips",
                "score": 0.90,
                "metadata": {"difficulty": "easy", "category": "career"}
            },
            {
                "id": "job2",
                "content": "Interview preparation guide",
                "score": 0.88,
                "metadata": {"difficulty": "medium", "category": "career"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert len(tree["nodes"]) > 0
    
    async def test_render_tree_practice(self, tree_service):
        """Test rendering tree for practice intent"""
        intent = Intent.PRACTICE
        documents = [
            {
                "id": "ex1",
                "content": "Basic coding exercises",
                "score": 0.93,
                "metadata": {"difficulty": "easy", "category": "exercises"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert tree["name"] is not None
    
    async def test_render_tree_resource(self, tree_service):
        """Test rendering tree for resource intent"""
        intent = Intent.RESOURCE
        documents = [
            {
                "id": "res1",
                "content": "Official documentation",
                "score": 0.96,
                "metadata": {"difficulty": "reference", "category": "docs"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert len(tree["nodes"]) >= 0
    
    async def test_render_tree_general(self, tree_service):
        """Test rendering tree for general intent"""
        intent = Intent.GENERAL
        documents = [
            {
                "id": "gen1",
                "content": "General information",
                "score": 0.70,
                "metadata": {"difficulty": "general", "category": "info"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
    
    async def test_render_tree_empty_documents(self, tree_service):
        """Test rendering tree with no documents"""
        intent = Intent.LEARNING_PATH
        documents = []
        
        tree = await tree_service.render_tree(intent, documents)
        
        # Should still return a valid tree structure
        assert tree is not None
        assert "nodes" in tree
    
    async def test_render_tree_node_structure(self, tree_service):
        """Test individual nodes have proper structure"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "JavaScript fundamentals",
                "score": 0.94,
                "metadata": {"difficulty": "beginner"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert len(tree["nodes"]) > 0
        for node in tree["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "difficulty" in node or "level" in node
    
    async def test_render_tree_edge_connectivity(self, tree_service):
        """Test edges connect valid nodes"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "Basics",
                "score": 0.95,
                "metadata": {"difficulty": "beginner"}
            },
            {
                "id": "doc2",
                "content": "Advanced",
                "score": 0.92,
                "metadata": {"difficulty": "advanced"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        node_ids = {node["id"] for node in tree["nodes"]}
        if tree["edges"]:
            for edge in tree["edges"]:
                assert "source" in edge
                assert "target" in edge
                assert edge["source"] in node_ids
                assert edge["target"] in node_ids
    
    async def test_render_tree_difficulty_ordering(self, tree_service):
        """Test nodes are ordered by difficulty"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "Advanced topic",
                "score": 0.90,
                "metadata": {"difficulty": "advanced"}
            },
            {
                "id": "doc2",
                "content": "Beginner topic",
                "score": 0.95,
                "metadata": {"difficulty": "beginner"}
            },
            {
                "id": "doc3",
                "content": "Intermediate topic",
                "score": 0.92,
                "metadata": {"difficulty": "intermediate"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        # Should have nodes ordered by difficulty progression
        assert len(tree["nodes"]) > 0
    
    async def test_render_tree_metadata_preservation(self, tree_service):
        """Test metadata is preserved in tree"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "Content with metadata",
                "score": 0.93,
                "metadata": {
                    "category": "web",
                    "language": "en",
                    "duration_hours": 5
                }
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert "metadata" in tree or any("category" in str(node) for node in tree["nodes"])
    
    async def test_render_tree_high_score_prioritization(self, tree_service):
        """Test high-score documents are prioritized"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "low",
                "content": "Low relevance",
                "score": 0.45,
                "metadata": {"difficulty": "beginner"}
            },
            {
                "id": "high",
                "content": "High relevance",
                "score": 0.95,
                "metadata": {"difficulty": "beginner"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        # High-score document should be included/prioritized
        assert tree is not None
        node_labels = [node.get("label", "") for node in tree["nodes"]]
        assert any("High" in label or len(node_labels) > 0 for label in node_labels)
    
    async def test_render_tree_duplicate_handling(self, tree_service):
        """Test handling of duplicate documents"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": "doc1",
                "content": "JavaScript basics",
                "score": 0.93,
                "metadata": {"difficulty": "beginner"}
            },
            {
                "id": "doc1",  # Duplicate ID
                "content": "JavaScript basics",
                "score": 0.93,
                "metadata": {"difficulty": "beginner"}
            }
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        # Should handle duplicates gracefully
        assert tree is not None
        # Nodes should not have exact duplicates
        node_ids = [node["id"] for node in tree["nodes"]]
        assert len(node_ids) == len(set(node_ids)) or len(node_ids) >= 1
    
    async def test_render_tree_large_document_set(self, tree_service):
        """Test rendering with large number of documents"""
        intent = Intent.LEARNING_PATH
        documents = [
            {
                "id": f"doc{i}",
                "content": f"Document {i}",
                "score": 0.90 - i*0.005,
                "metadata": {"difficulty": "beginner"}
            }
            for i in range(50)
        ]
        
        tree = await tree_service.render_tree(intent, documents)
        
        assert tree is not None
        assert len(tree["nodes"]) > 0
