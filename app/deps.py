# Dependency Injection
# Wiring ports ↔ adapters

from functools import lru_cache
from typing import Generator

from infrastructure.database.connection import get_db, AsyncSession
from infrastructure.llm.gemini_adapter import GeminiAdapter
from infrastructure.vector_store.chroma_adapter import ChromaAdapter
from infrastructure.embeddings.sentence_transformer_adapter import SentenceTransformerAdapter
from infrastructure.sync.sync_service import SyncService

from domain.services import ChatbotService, LearningService


# ============================================================
# SINGLETON INSTANCES (cached)
# ============================================================

@lru_cache()
def get_embedder() -> SentenceTransformerAdapter:
    """Get singleton embedder instance"""
    return SentenceTransformerAdapter()


@lru_cache()
def get_vector_store() -> ChromaAdapter:
    """Get singleton vector store instance"""
    embedder = get_embedder()
    return ChromaAdapter(
        db_path="../chroma_db",
        collection_name="ksa_project",
        embedder=embedder
    )


@lru_cache()
def get_llm() -> GeminiAdapter:
    """Get singleton LLM instance"""
    return GeminiAdapter()


@lru_cache()
def get_sync_service() -> SyncService:
    """Get singleton sync service"""
    vector_store = get_vector_store()
    embedder = get_embedder()
    return SyncService(vector_store, embedder)


# ============================================================
# SERVICE FACTORIES (with DB dependency)
# ============================================================

async def get_chatbot_service(db: AsyncSession = None):
    """Get chatbot service instance"""
    llm = get_llm()
    vector_store = get_vector_store()
    # TODO: Implement ChatRepositoryImpl
    return ChatbotService(llm, vector_store, None)


async def get_learning_service(db: AsyncSession = None):
    """Get learning service instance"""
    # TODO: Implement repositories
    return LearningService(None, None)


# ============================================================
# TEMPORARY MOCK SERVICES (for testing)
# ============================================================

class MockSkillService:
    """Mock service for Admin API - replace with real implementation"""
    
    async def get_all_templates(self):
        return []
    
    async def create_template(self, data: dict):
        from uuid import uuid4
        from datetime import datetime
        return {
            "id": str(uuid4()),
            "name": data.get("name", "New Template"),
            "description": data.get("description"),
            "category": data.get("category"),
            "is_active": True,
            "node_count": 0,
            "created_at": datetime.now()
        }
    
    async def get_template(self, template_id: str):
        return None
    
    async def delete_template(self, template_id: str):
        pass
    
    async def get_template_nodes(self, template_id: str):
        return []
    
    async def create_node(self, data: dict):
        from uuid import uuid4
        from datetime import datetime
        from domain.entities import SkillNode, NodeType, DifficultyLevel
        
        return SkillNode(
            id=uuid4(),
            name=data.get("name", "New Node"),
            description=data.get("description"),
            node_type=NodeType(data.get("node_type", "knowledge")),
            difficulty_level=DifficultyLevel(data.get("difficulty_level", "beginner")),
            estimated_hours=data.get("estimated_hours"),
            keywords=data.get("keywords", []),
            position_x=data.get("position_x"),
            position_y=data.get("position_y")
        )
    
    async def get_node(self, node_id: str):
        return None
    
    async def update_node(self, node_id: str, data: dict):
        return await self.create_node(data)
    
    async def delete_node(self, node_id: str):
        pass
    
    async def get_node_children(self, node_id: str):
        return []
    
    async def create_resource(self, data: dict):
        from uuid import uuid4
        from domain.entities import LearningResource, ResourceType
        
        return LearningResource(
            id=uuid4(),
            skill_node_id=data.get("skill_node_id"),
            title=data.get("title", "New Resource"),
            url=data.get("url"),
            resource_type=ResourceType(data.get("resource_type", "article")),
            platform=data.get("platform"),
            estimated_duration=data.get("estimated_duration"),
            is_free=data.get("is_free", True)
        )
    
    async def get_node_resources(self, node_id: str):
        return []
    
    async def delete_resource(self, resource_id: str):
        pass
    
    async def get_all_skills(self):
        return []


def get_skill_service() -> MockSkillService:
    """Get skill service - replace with real implementation"""
    return MockSkillService()
