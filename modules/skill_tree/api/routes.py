from fastapi import APIRouter, Depends, Query, HTTPException

from typing import List, Optional
from uuid import UUID

from modules.auth.api.deps import get_current_user_id
from modules.auth.api.deps import get_current_user_id

router = APIRouter(prefix="/skill-tree", tags=["Skill Tree"])

from .schemas import ResourceResponse

# Class definition removed, imported from schemas

from .deps import get_node_resources_usecase
from modules.skill_tree.usecases.get_resources import GetNodeResourcesUseCase

@router.get("/nodes/{node_id}/resources", response_model=List[ResourceResponse])
async def get_node_resources(
    node_id: str,
    node_name: Optional[str] = Query(None),
    user_id: UUID = Depends(get_current_user_id),
    usecase: GetNodeResourcesUseCase = Depends(get_node_resources_usecase)
):
    """
    Get learning resources for a specific node.
    """
    return await usecase.execute(node_id, user_id)


from .deps import get_session_skill_tree_usecase
from modules.skill_tree.usecases.get_tree import GetSessionSkillTreeUseCase

@router.get("/session/{session_id}")
async def get_session_skill_tree(
    session_id: str,
    user_id: UUID = Depends(get_current_user_id),
    usecase: GetSessionSkillTreeUseCase = Depends(get_session_skill_tree_usecase)
):
    """
    Get the skill tree for a specific chat session (or user active tree).
    """
    return await usecase.execute(session_id, user_id)


from .schemas import ResourceUpdateRequest
from modules.skill_tree.usecases.update_progress import UpdateResourceProgressUseCase
from .deps import get_update_resource_progress_usecase

@router.patch("/resources/{resource_id}/progress")
async def update_resource_progress(
    resource_id: str,
    data: ResourceUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    usecase: UpdateResourceProgressUseCase = Depends(get_update_resource_progress_usecase)
):
    """
    Update learning progress (status, percentage) for a resource.
    """
    return await usecase.execute(resource_id, user_id, data.status, data.progress_percent)


from modules.skill_tree.infrastructure.repository import get_skill_tree_repository

@router.get("/nodes/{node_id}/children")
async def get_node_children(
    node_id: str,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    LAZY LOADING: Get children (level 2 + level 3) of a specific node.
    Called when user clicks on a level 1 node to expand its subtree.
    """
    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node_id format")
    
    repo = get_skill_tree_repository()
    result = await repo.get_node_children(node_uuid)
    
    if result is None:
        return {"nodes": [], "edges": []}
    
    return result
