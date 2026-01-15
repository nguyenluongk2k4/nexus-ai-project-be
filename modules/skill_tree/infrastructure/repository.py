# Skill Tree Repository - PostgreSQL Queries
# Following DDD-lite: Repository belongs to infrastructure layer

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from shared.database.connection import get_db_context
from modules.skill_tree.domain.ports import SkillTreePort

from modules.skill_tree.infrastructure.models import (
    TemplateSkillNodeModel,
    TemplateSkillPathModel,
    LearningResourceModel,
    SkillTreeTemplateModel,
    LearningProgressModel,
    UserSkillTreeModel,
    UserSkillNodeModel,
    TemplateSkillNodeModel
)


class SkillTreeRepository(SkillTreePort):
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
    
    async def get_resources_for_nodes(self, node_ids: List[str], user_id: UUID) -> dict:
        """Get learning resources for multiple nodes with user progress"""
        async with get_db_context() as session:
            uuid_ids = [UUID(id) for id in node_ids if id]
            
            # Join with LearningProgressModel to get status/progress for this user
            stmt = (
                select(LearningResourceModel, LearningProgressModel)
                .outerjoin(
                    LearningProgressModel, 
                    (LearningProgressModel.resource_id == LearningResourceModel.id) & 
                    (LearningProgressModel.user_id == user_id)
                )
                .where(LearningResourceModel.skill_node_id.in_(uuid_ids))
                .order_by(LearningResourceModel.sort_order)
            )
            
            result = await session.execute(stmt)
            
            resources = {}
            for resource, progress in result.all():
                node_id = str(resource.skill_node_id)
                if node_id not in resources:
                    resources[node_id] = []
                
                # Default values if no progress found
                status = "not_started"
                progress_percent = 0
                
                if progress:
                    status = progress.status
                    progress_percent = progress.progress_percent

                resources[node_id].append({
                    "id": str(resource.id),
                    "title": resource.title,
                    "url": resource.url,
                    "type": resource.resource_type,
                    "platform": resource.platform,
                    "duration_minutes": resource.estimated_duration,
                    "is_free": resource.is_free,
                    "status": status,
                    "progress_percent": progress_percent
                })
            
            return resources
    

    async def update_resource_progress(self, user_id: UUID, resource_id: str, status: str, progress_percent: int) -> any:
        """Update or create learning progress for a resource"""
        async with get_db_context() as session:
            r_id = UUID(resource_id)
            
            # Check if progress exists
            stmt = select(LearningProgressModel).where(
                LearningProgressModel.user_id == user_id,
                LearningProgressModel.resource_id == r_id
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()
            
            if progress:
                # Update existing
                progress.status = status
                progress.progress_percent = progress_percent
                progress.updated_at = datetime.now()
            else:
                # Create new
                progress = LearningProgressModel(
                    user_id=user_id,
                    resource_id=r_id,
                    status=status,
                    progress_percent=progress_percent
                )
                session.add(progress)
            
            await session.commit()
            return progress

    async def get_user_tree(self, user_id: UUID) -> Optional[dict]:
        """Get the user's active skill tree. If none, return default Template tree structure."""
        async with get_db_context() as session:
            # 1. Try to find existing User Tree
            stmt = select(UserSkillTreeModel).where(UserSkillTreeModel.user_id == user_id).limit(1)
            result = await session.execute(stmt)
            user_tree = result.scalar_one_or_none()
            
            if user_tree:
                # TODO: Implement full user tree fetching (nodes + edges)
                # For now, if user tree exists, we return it.
                # Since we don't have a seed script for UserTrees yet in Phase 2, this path might be empty.
                pass
            
            # 2. Fallback: Return the Default Template Tree (acting as a "View" of the template)
            # This ensures Phase 2 works immediately without needing to clone data yet.
            # We assume there is at least one active template.
            stmt_template = select(SkillTreeTemplateModel).where(SkillTreeTemplateModel.is_active == True).limit(1)
            result_template = await session.execute(stmt_template)
            template = result_template.scalar_one_or_none()
            
            if not template:
                return None
                
            # Fetch nodes for this template
            nodes_result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.template_id == template.id)
            )
            nodes = nodes_result.scalars().all()
            
            # Fetch edges (hierarchy)
            # We need all edges where both ancestor and descendant are in our node list
            # Simplify: Get all paths for this template's nodes
            # (Check complexity: if template is large, this is heavy. But skill trees are usually < 100 nodes)
            
            # Construct response
            tree_data = {
                "id": str(template.id),
                "name": template.name,
                "nodes": [],
                "edges": []
            }
            
            node_map = {}
            for node in nodes:
                n_id = str(node.id)
                node_map[n_id] = True
                tree_data["nodes"].append({
                    "id": n_id,
                    "label": node.name,
                    "type": "skill", # default
                    "data": {
                        "description": node.description,
                        "status": "not_started" # Default status since we are viewing template
                    },
                    "position": { "x": node.position_x or 0, "y": node.position_y or 0 }
                })

            # Fetch edges: ancestor -> descendant where depth=1 (direct parent)
            # This builds the graph edges.
            node_uuids = [n.id for n in nodes]
            if node_uuids:
                edges_stmt = (
                    select(TemplateSkillPathModel)
                    .where(
                        TemplateSkillPathModel.depth == 1,
                        TemplateSkillPathModel.ancestor_id.in_(node_uuids),
                        TemplateSkillPathModel.descendant_id.in_(node_uuids)
                    )
                )
                edges_result = await session.execute(edges_stmt)
                
                for edge in edges_result.scalars().all():
                    tree_data["edges"].append({
                        "id": f"e{edge.ancestor_id}-{edge.descendant_id}",
                        "source": str(edge.ancestor_id),
                        "target": str(edge.descendant_id),
                        "animated": True
                    })
            
            return tree_data



# Singleton instance
_repository: Optional[SkillTreeRepository] = None

def get_skill_tree_repository() -> SkillTreeRepository:
    """Get or create singleton SkillTreeRepository"""
    global _repository
    if _repository is None:
        _repository = SkillTreeRepository()
    return _repository
