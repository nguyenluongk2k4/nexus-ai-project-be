# Admin Module - Providers (Dependency Injection)

from functools import lru_cache
from typing import List

from modules.admin.domain.entities import SkillNode, LearningResource


class SyncService:
    """Service đồng bộ dữ liệu từ PostgreSQL sang ChromaDB"""
    
    def __init__(self, vector_store, embedder):
        self.vector = vector_store
        self.embedder = embedder
    
    def sync_skill_node(self, skill) -> None:
        """Sync 1 skill node vào ChromaDB"""
        text = self._build_skill_text(skill)
        embedding = self.embedder.encode(text).tolist()
        
        skill_id = str(skill.id) if hasattr(skill, 'id') else str(skill.get('id', ''))
        try:
            self.vector.collection.delete(ids=[skill_id])
        except:
            pass
        
        self.vector.collection.add(
            ids=[skill_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "type": getattr(skill, 'node_type', 'knowledge'),
                "name": getattr(skill, 'name', skill.get('name', '')) if hasattr(skill, 'name') else skill.get('name', '')
            }]
        )
        print(f"✅ Synced skill: {skill_id}")
    
    def delete_skill_from_vector(self, skill_id: str) -> None:
        """Xóa skill khỏi ChromaDB"""
        try:
            self.vector.collection.delete(ids=[skill_id])
            print(f"✅ Deleted skill from vector store: {skill_id}")
        except Exception as e:
            print(f"⚠️ Failed to delete from vector store: {e}")
    
    def sync_resource(self, resource, skill_name: str = "") -> None:
        """Sync 1 learning resource vào ChromaDB"""
        title = getattr(resource, 'title', resource.get('title', '')) if hasattr(resource, 'title') else resource.get('title', '')
        platform = getattr(resource, 'platform', resource.get('platform', 'Unknown')) if hasattr(resource, 'platform') else resource.get('platform', 'Unknown')
        text = f"{title}. {skill_name}. Platform: {platform}"
        
        embedding = self.embedder.encode(text).tolist()
        resource_id = str(resource.id) if hasattr(resource, 'id') else str(resource.get('id', ''))
        
        try:
            self.vector.collection.delete(ids=[resource_id])
        except:
            pass
        
        self.vector.collection.add(
            ids=[resource_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{"type": "resource"}]
        )
    
    def rebuild_index(self, skills: List) -> int:
        """Xóa toàn bộ và rebuild index từ PostgreSQL"""
        try:
            all_data = self.vector.collection.get()
            if all_data['ids']:
                self.vector.collection.delete(ids=all_data['ids'])
            print("🗑️ Cleared vector store")
        except Exception as e:
            print(f"⚠️ Error clearing: {e}")
        
        count = 0
        for skill in skills:
            try:
                self.sync_skill_node(skill)
                count += 1
            except Exception as e:
                print(f"❌ Failed to sync: {e}")
        return count
    
    def _build_skill_text(self, skill) -> str:
        """Tạo text searchable từ skill data"""
        name = getattr(skill, 'name', skill.get('name', '')) if hasattr(skill, 'name') else skill.get('name', '')
        parts = [name]
        
        desc = getattr(skill, 'description', skill.get('description')) if hasattr(skill, 'description') else skill.get('description')
        if desc:
            parts.append(desc)
        
        keywords = getattr(skill, 'keywords', skill.get('keywords', [])) if hasattr(skill, 'keywords') else skill.get('keywords', [])
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        
        return ". ".join(parts)


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
            "icon": data.get("icon"),
            "color": data.get("color"),
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
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
        return {
            "id": str(uuid4()),
            "template_id": data.get("template_id"),
            "name": data.get("name", "New Node"),
            "description": data.get("description"),
            "node_type": data.get("node_type", "knowledge"),
            "difficulty_level": data.get("difficulty_level"),
            "estimated_hours": data.get("estimated_hours"),
            "keywords": data.get("keywords", []),
            "position_x": data.get("position_x"),
            "position_y": data.get("position_y"),
            "created_at": datetime.now()
        }
    
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
        return {
            "id": str(uuid4()),
            "skill_node_id": data.get("skill_node_id"),
            "title": data.get("title", "New Resource"),
            "url": data.get("url"),
            "resource_type": data.get("resource_type", "article"),
            "platform": data.get("platform"),
            "estimated_duration": data.get("estimated_duration"),
            "is_free": data.get("is_free", True),
            "sort_order": data.get("sort_order", 0)
        }
    
    async def get_node_resources(self, node_id: str):
        return []
    
    async def delete_resource(self, resource_id: str):
        pass
    
    async def get_all_skills(self):
        return []


# Singleton instances
_skill_service = None
_sync_service = None


def get_skill_service():
    """Get skill service instance"""
    global _skill_service
    if _skill_service is None:
        _skill_service = MockSkillService()
    return _skill_service


def get_sync_service():
    """Get sync service instance"""
    global _sync_service
    if _sync_service is None:
        from modules.chat.providers import get_vector_store
        vector_store = get_vector_store()
        _sync_service = SyncService(vector_store, vector_store.embedder)
    return _sync_service
