# Skill Tree Repository - PostgreSQL Queries
# Following DDD-lite: Repository belongs to infrastructure layer

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from shared.database.connection import get_db_context
from modules.skill_tree.infrastructure.models import (
    TemplateSkillNodeModel,
    TemplateSkillPathModel,
    LearningResourceModel,
    SkillTreeTemplateModel
)


class SkillTreeRepository:
    """Repository for querying skill tree data from PostgreSQL"""
    
    async def get_nodes_by_ids(self, node_ids: List[str]) -> List[TemplateSkillNodeModel]:
        """Get multiple nodes by their IDs"""
        async with get_db_context() as session:
            # Convert string IDs to UUIDs
            uuid_ids = [UUID(id) for id in node_ids if id]
            
            result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.id.in_(uuid_ids))
            )
            return list(result.scalars().all())
    
    async def get_node_by_id(self, node_id: str) -> Optional[TemplateSkillNodeModel]:
        """Get a single node by ID"""
        async with get_db_context() as session:
            result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.id == UUID(node_id))
            )
            return result.scalar_one_or_none()
    
    async def search_nodes_by_name(self, query: str, limit: int = 20) -> List[TemplateSkillNodeModel]:
        """Search nodes by name (ILIKE pattern matching)"""
        async with get_db_context() as session:
            result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.name.ilike(f"%{query}%"))
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def get_node_hierarchy(self, node_id: str) -> List[dict]:
        """
        Get node hierarchy using closure table (template_skill_paths)
        Returns ancestors and descendants of a node
        """
        async with get_db_context() as session:
            uuid_id = UUID(node_id)
            
            # Get descendants (this node is ancestor)
            descendants_result = await session.execute(
                select(TemplateSkillPathModel, TemplateSkillNodeModel)
                .join(TemplateSkillNodeModel, TemplateSkillPathModel.descendant_id == TemplateSkillNodeModel.id)
                .where(TemplateSkillPathModel.ancestor_id == uuid_id)
            )
            
            # Get ancestors (this node is descendant)
            ancestors_result = await session.execute(
                select(TemplateSkillPathModel, TemplateSkillNodeModel)
                .join(TemplateSkillNodeModel, TemplateSkillPathModel.ancestor_id == TemplateSkillNodeModel.id)
                .where(TemplateSkillPathModel.descendant_id == uuid_id)
            )
            
            hierarchy = []
            for path, node in descendants_result:
                hierarchy.append({
                    "node_id": str(node.id),
                    "name": node.name,
                    "depth": path.depth,
                    "relation": "descendant"
                })
            for path, node in ancestors_result:
                hierarchy.append({
                    "node_id": str(node.id),
                    "name": node.name,
                    "depth": path.depth,
                    "relation": "ancestor"
                })
            
            return hierarchy
    
    async def get_node_parent(self, node_id: str) -> Optional[str]:
        """Get immediate parent of a node (depth=1 in closure table)"""
        async with get_db_context() as session:
            uuid_id = UUID(node_id)
            
            result = await session.execute(
                select(TemplateSkillPathModel.ancestor_id)
                .where(
                    TemplateSkillPathModel.descendant_id == uuid_id,
                    TemplateSkillPathModel.depth == 1
                )
            )
            parent_id = result.scalar_one_or_none()
            return str(parent_id) if parent_id else None
    
    async def get_resources_for_nodes(self, node_ids: List[str]) -> dict:
        """Get learning resources for multiple nodes"""
        async with get_db_context() as session:
            uuid_ids = [UUID(id) for id in node_ids if id]
            
            result = await session.execute(
                select(LearningResourceModel)
                .where(LearningResourceModel.skill_node_id.in_(uuid_ids))
                .order_by(LearningResourceModel.sort_order)
            )
            
            resources = {}
            for resource in result.scalars().all():
                node_id = str(resource.skill_node_id)
                if node_id not in resources:
                    resources[node_id] = []
                resources[node_id].append({
                    "id": str(resource.id),
                    "title": resource.title,
                    "url": resource.url,
                    "type": resource.resource_type,
                    "platform": resource.platform,
                    "duration_minutes": resource.estimated_duration,
                    "is_free": resource.is_free
                })
            
            return resources
    
    async def get_all_templates(self) -> List[SkillTreeTemplateModel]:
        """Get all skill tree templates"""
        async with get_db_context() as session:
            result = await session.execute(
                select(SkillTreeTemplateModel)
                .where(SkillTreeTemplateModel.is_active == True)
            )
            return list(result.scalars().all())


# Singleton instance
_repository: Optional[SkillTreeRepository] = None

def get_skill_tree_repository() -> SkillTreeRepository:
    """Get or create singleton SkillTreeRepository"""
    global _repository
    if _repository is None:
        _repository = SkillTreeRepository()
    return _repository
