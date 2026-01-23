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
    UserSkillPathModel
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
        """Get the user's active skill tree. If none, return default Template tree structure.
        OPTIMIZED: Returns only root + first 2 levels (max ~20 nodes) for initial load.
        """
        MAX_INITIAL_NODES = 20  # Limit for initial load
        
        async with get_db_context() as session:
            # 1. Try to find existing User Tree
            stmt = select(UserSkillTreeModel).where(UserSkillTreeModel.user_id == user_id).limit(1)
            result = await session.execute(stmt)
            user_tree = result.scalar_one_or_none()
            
            if user_tree:
                # TODO: Implement full user tree fetching with same limits
                pass
            
            # 2. Fallback: Return the Default Template Tree
            stmt_template = select(SkillTreeTemplateModel).where(SkillTreeTemplateModel.is_active == True).limit(1)
            result_template = await session.execute(stmt_template)
            template = result_template.scalar_one_or_none()
            
            if not template:
                return None
            
            # === OPTIMIZED: Find root nodes first, then get only first 2 levels ===
            
            # Step 1: Get root nodes (nodes without parents)
            # A node is root if it's not in any descendant_id of depth=1 paths
            all_nodes_stmt = select(TemplateSkillNodeModel.id).where(
                TemplateSkillNodeModel.template_id == template.id
            )
            all_nodes_result = await session.execute(all_nodes_stmt)
            all_node_ids = [row[0] for row in all_nodes_result.fetchall()]
            
            # Get all nodes that ARE descendants (have parents)
            children_stmt = select(TemplateSkillPathModel.descendant_id).where(
                TemplateSkillPathModel.depth == 1,
                TemplateSkillPathModel.descendant_id.in_(all_node_ids)
            ).distinct()
            children_result = await session.execute(children_stmt)
            child_ids = set(row[0] for row in children_result.fetchall())
            
            # Root nodes = all_nodes - children
            root_ids = [nid for nid in all_node_ids if nid not in child_ids]
            
            # Step 2: Get level 1 children (direct children of roots)
            level1_stmt = select(TemplateSkillPathModel.descendant_id).where(
                TemplateSkillPathModel.depth == 1,
                TemplateSkillPathModel.ancestor_id.in_(root_ids)
            )
            level1_result = await session.execute(level1_stmt)
            level1_ids = [row[0] for row in level1_result.fetchall()]  # All level 1 nodes
            
            # LAZY LOADING: Only return level 0 + 1 initially
            # Level 2 and 3 will be loaded via GET /nodes/{id}/children
            selected_node_ids = list(set(root_ids + level1_ids))
            
            # Build level map for each node
            level_map = {}
            for nid in root_ids:
                level_map[nid] = 0
            for nid in level1_ids:
                level_map[nid] = 1
            
            # Fetch only selected nodes
            nodes_result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.id.in_(selected_node_ids))
            )
            nodes = nodes_result.scalars().all()
            
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
                node_level = level_map.get(node.id, 0)
                node_map[n_id] = True
                
                # Determine node type based on level
                node_type = "root" if node_level == 0 else ("ability" if node_level == 1 else "skill")
                
                tree_data["nodes"].append({
                    "id": n_id,
                    "label": node.name,
                    "type": node_type,
                    "level": node_level,  # CRITICAL: Frontend needs this for tree layout
                    "data": {
                        "description": node.description,
                        "status": "not_started"
                    },
                    "position": { "x": node.position_x or 0, "y": node.position_y or 0 }
                })

            # Fetch edges only for selected nodes
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

    async def get_node_children(self, node_id: UUID) -> Optional[dict]:
        """
        LAZY LOADING: Fetch all children (level 2 + level 3 relative to the node) 
        when user clicks on a level 1 node.
        Returns nodes and edges for the clicked node's subtree.
        """
        async with get_db_context() as session:
            # Get direct children (level 2)
            level2_stmt = select(TemplateSkillPathModel.descendant_id).where(
                TemplateSkillPathModel.depth == 1,
                TemplateSkillPathModel.ancestor_id == node_id
            )
            level2_result = await session.execute(level2_stmt)
            level2_ids = [row[0] for row in level2_result.fetchall()]
            
            # Get grandchildren (level 3)
            level3_ids = []
            if level2_ids:
                level3_stmt = select(TemplateSkillPathModel.descendant_id).where(
                    TemplateSkillPathModel.depth == 1,
                    TemplateSkillPathModel.ancestor_id.in_(level2_ids)
                )
                level3_result = await session.execute(level3_stmt)
                level3_ids = [row[0] for row in level3_result.fetchall()]
            
            # Combine all child IDs
            all_child_ids = list(set(level2_ids + level3_ids))
            
            if not all_child_ids:
                return {"nodes": [], "edges": []}
            
            # Build level map
            level_map = {}
            for nid in level2_ids:
                level_map[nid] = 2
            for nid in level3_ids:
                level_map[nid] = 3
            
            # Fetch nodes
            nodes_result = await session.execute(
                select(TemplateSkillNodeModel)
                .where(TemplateSkillNodeModel.id.in_(all_child_ids))
            )
            nodes = nodes_result.scalars().all()
            
            # Build response
            result = {"nodes": [], "edges": []}
            
            for node in nodes:
                n_id = str(node.id)
                node_level = level_map.get(node.id, 2)
                node_type = "skill" if node_level == 2 else "knowledge"
                
                result["nodes"].append({
                    "id": n_id,
                    "label": node.name,
                    "type": node_type,
                    "level": node_level,
                    "data": {
                        "description": node.description,
                        "status": "not_started"
                    },
                    "position": {"x": node.position_x or 0, "y": node.position_y or 0}
                })
            
            # Fetch edges: parent node → level2, level2 → level3
            all_ids_with_parent = [node_id] + all_child_ids
            edges_stmt = (
                select(TemplateSkillPathModel)
                .where(
                    TemplateSkillPathModel.depth == 1,
                    TemplateSkillPathModel.ancestor_id.in_(all_ids_with_parent),
                    TemplateSkillPathModel.descendant_id.in_(all_child_ids)
                )
            )
            edges_result = await session.execute(edges_stmt)
            
            for edge in edges_result.scalars().all():
                result["edges"].append({
                    "id": f"e{edge.ancestor_id}-{edge.descendant_id}",
                    "source": str(edge.ancestor_id),
                    "target": str(edge.descendant_id),
                    "animated": True
                })
            
            return result

    # =============== USER SKILL TREE METHODS ===============
    
    async def get_or_create_user_tree(self, user_id: UUID, name: str = "My Learning Path") -> UserSkillTreeModel:
        """Get existing user tree or create a new one"""
        async with get_db_context() as session:
            # Try to find existing tree
            result = await session.execute(
                select(UserSkillTreeModel).where(UserSkillTreeModel.user_id == user_id).limit(1)
            )
            user_tree = result.scalar_one_or_none()
            
            if user_tree:
                return user_tree
            
            # Create new tree
            new_tree = UserSkillTreeModel(
                user_id=user_id,
                name=name
            )
            session.add(new_tree)
            await session.commit()
            await session.refresh(new_tree)
            return new_tree

    async def get_full_user_tree(self, user_id: UUID) -> Optional[dict]:
        """Get user's skill tree with all nodes and edges"""
        async with get_db_context() as session:
            # Get user's tree
            result = await session.execute(
                select(UserSkillTreeModel).where(UserSkillTreeModel.user_id == user_id).limit(1)
            )
            user_tree = result.scalar_one_or_none()
            
            if not user_tree:
                return None
            
            # Get all nodes for this tree
            nodes_result = await session.execute(
                select(UserSkillNodeModel).where(UserSkillNodeModel.tree_id == user_tree.id)
            )
            nodes = nodes_result.scalars().all()
            
            if not nodes:
                return {
                    "id": str(user_tree.id),
                    "name": user_tree.name,
                    "nodes": [],
                    "edges": []
                }
            
            # Get paths (edges) for hierarchy
            node_ids = [n.id for n in nodes]
            paths_result = await session.execute(
                select(UserSkillPathModel).where(
                    UserSkillPathModel.depth == 1,
                    UserSkillPathModel.ancestor_id.in_(node_ids),
                    UserSkillPathModel.descendant_id.in_(node_ids)
                )
            )
            paths = paths_result.scalars().all()
            
            # Build level map from paths (root = no parent)
            child_ids = set(p.descendant_id for p in paths)
            parent_map = {p.descendant_id: p.ancestor_id for p in paths}
            
            def get_level(node_id, depth=0):
                if node_id not in parent_map:
                    return depth
                return get_level(parent_map[node_id], depth + 1)
            
            # Construct response
            tree_data = {
                "id": str(user_tree.id),
                "name": user_tree.name,
                "nodes": [],
                "edges": []
            }
            
            for node in nodes:
                level = get_level(node.id)
                parent_id = str(parent_map[node.id]) if node.id in parent_map else None
                
                tree_data["nodes"].append({
                    "id": str(node.id),
                    "name": node.name,
                    "description": node.description,
                    "status": node.status,
                    "progress_percent": node.progress_percent,
                    "level": level,
                    "parent_id": parent_id,
                    "icon": node.icon,
                    "color": node.color
                })
            
            for path in paths:
                tree_data["edges"].append({
                    "source": str(path.ancestor_id),
                    "target": str(path.descendant_id)
                })
            
            return tree_data

    async def add_nodes_to_user_tree(
        self, 
        user_id: UUID, 
        session_id: str, 
        node_data: List[dict]
    ) -> dict:
        """
        Add nodes from chat session to user's tree.
        node_data: List of dicts with id, name, description, level, parentId
        """
        async with get_db_context() as session:
            # Get or create user tree
            result = await session.execute(
                select(UserSkillTreeModel).where(UserSkillTreeModel.user_id == user_id).limit(1)
            )
            user_tree = result.scalar_one_or_none()
            
            if not user_tree:
                user_tree = UserSkillTreeModel(
                    user_id=user_id,
                    name="My Learning Path"
                )
                session.add(user_tree)
                await session.flush()
            
            # Track old_id -> new_id mapping for paths
            id_mapping = {}
            new_nodes = []
            
            for node in node_data:
                # Check for original mapping in node data or metadata
                metadata = node.get("metadata") or {}
                orig_id = node.get("original_node_id") or metadata.get("original_node_id")
                
                # If no original mapping, but the ID itself is a UUID, it might be the template ID
                if not orig_id:
                    try:
                        node_id = str(node.get("id", ""))
                        if len(node_id) > 20: 
                            UUID(node_id)
                            orig_id = node_id
                    except (ValueError, TypeError):
                        pass

                new_node = UserSkillNodeModel(
                    tree_id=user_tree.id,
                    original_node_id=UUID(orig_id) if orig_id else None,
                    name=node.get("name", "Untitled"),
                    description=node.get("description"),
                    status="not_started",
                    progress_percent=0
                )
                session.add(new_node)
                await session.flush()
                
                id_mapping[node["id"]] = new_node.id
                new_nodes.append(new_node)
            
            # Create paths (edges) based on parentId
            for node in node_data:
                new_node_id = id_mapping[node["id"]]
                parent_id = node.get("parentId")
                
                # Self-reference path (depth=0)
                self_path = UserSkillPathModel(
                    ancestor_id=new_node_id,
                    descendant_id=new_node_id,
                    depth=0
                )
                session.add(self_path)
                
                # Parent-child path (depth=1)
                if parent_id and parent_id in id_mapping:
                    parent_path = UserSkillPathModel(
                        ancestor_id=id_mapping[parent_id],
                        descendant_id=new_node_id,
                        depth=1
                    )
                    session.add(parent_path)
            
            await session.commit()
            
            return {
                "status": "success",
                "tree_id": str(user_tree.id),
                "nodes_added": len(new_nodes)
            }

    async def remove_node_from_user_tree(self, user_id: UUID, node_id: str) -> bool:
        """Remove a node from user's tree (cascades to paths)"""
        async with get_db_context() as session:
            uuid_node_id = UUID(node_id)
            
            # Verify node belongs to user's tree
            result = await session.execute(
                select(UserSkillNodeModel)
                .join(UserSkillTreeModel)
                .where(
                    UserSkillNodeModel.id == uuid_node_id,
                    UserSkillTreeModel.user_id == user_id
                )
            )
            node = result.scalar_one_or_none()
            
            if not node:
                return False
            
            # Delete node (paths will cascade)
            await session.delete(node)
            await session.commit()
            return True



# Singleton instance
_repository: Optional[SkillTreeRepository] = None

def get_skill_tree_repository() -> SkillTreeRepository:
    """Get or create singleton SkillTreeRepository"""
    global _repository
    if _repository is None:
        _repository = SkillTreeRepository()
    return _repository

