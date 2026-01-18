from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

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
    session_id: Optional[str] = Query(None),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    LAZY LOADING: Get children of a specific node.
    Checks session context for generated trees, then falls back to database.
    """
    children_nodes = []
    
    # Step 1: Try session context first (for generated trees)
    if session_id:
        try:
            from modules.chat.infrastructure.repository import ChatRepositoryImpl
            chat_repo = ChatRepositoryImpl()
            session = await chat_repo.get_session(UUID(session_id))
            
            if session and session.context_data:
                tree_nodes = session.context_data.get("tree_nodes", [])
                if tree_nodes:
                    children_nodes = [n for n in tree_nodes if n.get("parentId") == node_id]
        except Exception as e:
            print(f"⚠️ Session context lookup failed: {e}")
    
    # Step 2: Fallback to database (for template trees)
    if not children_nodes:
        try:
            node_uuid = UUID(node_id)
            repo = get_skill_tree_repository()
            result = await repo.get_node_children(node_uuid)
            if result:
                return result  # DB already returns correct format
        except Exception as e:
            print(f"⚠️ DB lookup failed: {e}")
            return {"nodes": [], "edges": []}
    
    # Convert session context nodes to API format
    nodes = []
    edges = []
    for child in children_nodes:
        nodes.append({
            "id": child["id"],
            "label": child.get("name"),
            "type": child.get("type", "skill"),
            "level": child.get("level", 2),
            "data": {
                "description": child.get("description"),
                "status": "not_started"
            },
            "position": {"x": 0, "y": 0}
        })
        edges.append({
            "id": f"e{node_id}-{child['id']}",
            "source": node_id,
            "target": child["id"],
            "animated": True
        })
    
    print(f"🌳 Found {len(children_nodes)} children from session context")
    return {"nodes": nodes, "edges": edges}


from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

class TreeGenerateRequest(BaseModel):
    message: str
    session_id: str

@router.post("/generate")
async def generate_skill_tree(
    request: TreeGenerateRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Generate skill tree from user message using HTTP streaming.
    Returns SSE stream with status updates and final tree nodes.
    """
    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps({'status': 'generating', 'message': 'Đang tìm kiếm kiến thức phù hợp...'})}\n\n"
            await asyncio.sleep(0.1)  # Small delay for client to process
            
            # Import and use skill tree query service
            from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
            skill_tree_service = get_skill_tree_query_service()
            
            # Generate ALL tree nodes (no max_level filter for full tree)
            tree_nodes = await skill_tree_service.query(request.message)
            
            if tree_nodes:
                # Build ALL nodes data
                nodes_data = [
                    {
                        "id": node.id,
                        "name": node.name,
                        "description": node.description,
                        "type": node.type,
                        "parentId": node.parent_id,
                        "level": node.level,
                        "filled": True,
                        "metadata": node.metadata
                    }
                    for node in tree_nodes
                ]
                
                # Persist to session context
                try:
                    from modules.chat.infrastructure.repository import ChatRepositoryImpl
                    chat_repo = ChatRepositoryImpl()
                    await chat_repo.update_session_context(
                        UUID(request.session_id),
                        {"tree_nodes": nodes_data}
                    )
                    print(f"💾 Persisted {len(nodes_data)} nodes")
                except Exception as e:
                    print(f"⚠️ Could not persist tree: {e}")
                
                # Stream ALL nodes at once (no lazy loading)
                yield f"data: {json.dumps({'status': 'done', 'nodes': nodes_data, 'message': f'Tạo thành công {len(nodes_data)} nodes'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'done', 'nodes': [], 'message': 'Không tìm thấy kiến thức phù hợp'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
