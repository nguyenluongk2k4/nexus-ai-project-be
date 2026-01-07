# Sync Service - Đồng bộ PostgreSQL → ChromaDB
# Auto-sync khi CRUD skills

from typing import List, Optional
from uuid import UUID

from domain.entities import SkillNode, LearningResource
from domain.ports import VectorStorePort, EmbeddingPort


class SyncService:
    """
    Service đồng bộ dữ liệu từ PostgreSQL sang ChromaDB
    Được gọi tự động khi CRUD skills/resources
    """
    
    def __init__(self, vector_store: VectorStorePort, embedder: EmbeddingPort):
        self.vector = vector_store
        self.embedder = embedder
    
    def sync_skill_node(self, skill: SkillNode) -> None:
        """Sync 1 skill node vào ChromaDB"""
        # Tạo searchable text từ skill data
        text = self._build_skill_text(skill)
        
        # Embed text thành vector
        embedding = self.embedder.encode(text)
        
        # Upsert vào ChromaDB (delete if exists, then add)
        skill_id = str(skill.id)
        try:
            self.vector.collection.delete(ids=[skill_id])
        except:
            pass  # Ignore if not exists
        
        self.vector.collection.add(
            ids=[skill_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "type": skill.node_type.value if hasattr(skill.node_type, 'value') else str(skill.node_type),
                "difficulty": skill.difficulty_level.value if hasattr(skill.difficulty_level, 'value') else str(skill.difficulty_level),
                "name": skill.name
            }]
        )
        print(f"✅ Synced skill: {skill.name}")
    
    def delete_skill_from_vector(self, skill_id: str) -> None:
        """Xóa skill khỏi ChromaDB"""
        try:
            self.vector.collection.delete(ids=[skill_id])
            print(f"✅ Deleted skill from vector store: {skill_id}")
        except Exception as e:
            print(f"⚠️ Failed to delete from vector store: {e}")
    
    def sync_resource(self, resource: LearningResource, skill_name: str = "") -> None:
        """Sync 1 learning resource vào ChromaDB"""
        text = f"{resource.title}. {skill_name}. Platform: {resource.platform or 'Unknown'}"
        
        embedding = self.embedder.encode(text)
        resource_id = str(resource.id)
        
        try:
            self.vector.collection.delete(ids=[resource_id])
        except:
            pass
        
        self.vector.collection.add(
            ids=[resource_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "type": "resource",
                "resource_type": resource.resource_type.value if hasattr(resource.resource_type, 'value') else str(resource.resource_type),
                "is_free": resource.is_free
            }]
        )
    
    def bulk_sync_skills(self, skills: List[SkillNode]) -> int:
        """Sync nhiều skills cùng lúc"""
        count = 0
        for skill in skills:
            try:
                self.sync_skill_node(skill)
                count += 1
            except Exception as e:
                print(f"❌ Failed to sync {skill.name}: {e}")
        return count
    
    def rebuild_index(self, skills: List[SkillNode]) -> int:
        """Xóa toàn bộ và rebuild index từ PostgreSQL"""
        # Clear collection
        try:
            # Get all IDs and delete
            all_data = self.vector.collection.get()
            if all_data['ids']:
                self.vector.collection.delete(ids=all_data['ids'])
            print("🗑️ Cleared vector store")
        except Exception as e:
            print(f"⚠️ Error clearing: {e}")
        
        # Re-sync all
        return self.bulk_sync_skills(skills)
    
    def _build_skill_text(self, skill: SkillNode) -> str:
        """Tạo text searchable từ skill data"""
        parts = [skill.name]
        
        if skill.description:
            parts.append(skill.description)
        
        if skill.keywords:
            parts.append(f"Keywords: {', '.join(skill.keywords)}")
        
        return ". ".join(parts)
