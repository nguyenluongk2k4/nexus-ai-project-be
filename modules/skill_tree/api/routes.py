from fastapi import APIRouter, Depends, Query, HTTPException

from typing import List, Optional
from uuid import UUID

from modules.auth.api.deps import get_current_user_id
from modules.skill_tree.infrastructure.repository import get_skill_tree_repository

router = APIRouter(prefix="/skill-tree", tags=["Skill Tree"])

from .schemas import ResourceResponse

# Class definition removed, imported from schemas

@router.get("/nodes/{node_id}/resources", response_model=List[ResourceResponse])
async def get_node_resources(
    node_id: str,
    node_name: Optional[str] = Query(None),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get learning resources for a specific node.
    - If node_id is a UUID, fetches from DB.
    - If node_id is a placeholder (node-X), returns empty for now (future: search by name).
    """
    repo = get_skill_tree_repository()
    
    # 1. Try to fetch by ID if UUID
    # Simple check if it looks like a uuid (36 chars) or just try conversion
    is_uuid = False
    try:
        UUID(node_id)
        is_uuid = True
    except:
        pass

    if is_uuid:
        resources_map = await repo.get_resources_for_nodes([node_id])
        if resources_map and resources_map.get(node_id):
            return resources_map[node_id]
            
    # 2. If no ID or not found, fallback to name search is complex because 
    # we need to search RESOURCES by matching node name? 
    # Or find the node by name first?
    # For now, let's keep it simple: Real DB nodes get resources. Generated nodes don't.
    
    return []
