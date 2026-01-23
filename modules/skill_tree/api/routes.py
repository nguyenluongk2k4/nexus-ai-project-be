from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from typing import List, Optional
from uuid import UUID

from modules.auth.api.deps import get_current_user_id
from modules.auth.api.deps import get_current_user_id

router = APIRouter(prefix="/skill-tree", tags=["Skill Tree"])


from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from .schemas import ResourceResponse

# Class definition removed, imported from schemas

from .deps import get_node_resources_usecase
from modules.skill_tree.usecases.get_resources import GetNodeResourcesUseCase

@router.get("/nodes/{node_id}/resources", response_model=List[ResourceResponse])
async def get_node_resources(
    node_id: str,
    user_id: UUID = Depends(get_current_user_id),
    usecase: GetNodeResourcesUseCase = Depends(get_node_resources_usecase)
):
    """
    Get learning resources for a specific node.
    """
    result = await usecase.execute(node_id, user_id)
    # Ensure we always return a list, not dict
    if not result or isinstance(result, dict):
        return []
    return result


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
    print(f"\n🔍 [API] get_node_children called:")
    print(f"  - node_id: {node_id}")
    print(f"  - session_id: {session_id}")
    
    children_nodes = []
    
    # Step 1: Try session context first (for generated trees)
    if session_id:
        try:
            from modules.chat.infrastructure.repository import ChatRepositoryImpl
            chat_repo = ChatRepositoryImpl()
            session = await chat_repo.get_session(UUID(session_id))
            
            print(f"  - session found: {session is not None}")
            
            if session and session.context_data:
                tree_nodes = session.context_data.get("tree_nodes", [])
                print(f"  - tree_nodes count: {len(tree_nodes)}")
                if tree_nodes:
                    children_nodes = [n for n in tree_nodes if n.get("parentId") == node_id or n.get("parent_id") == node_id]
                    print(f"  - children found in session: {len(children_nodes)}")
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
    print(f"🌳 Found {len(children_nodes)} children from session context")
    return {"nodes": nodes, "edges": edges}

@router.get("/nodes/{node_id}/alternatives")
async def get_node_alternatives(
    node_id: str,
    level: int,
    session_id: Optional[str] = Query(None),
    node_name: Optional[str] = Query(None),
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get alternative nodes for a specific node to support swapping.
    Queries DB for node details and uses node name as search context.
    """
    from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
    from modules.skill_tree.infrastructure.repository import get_skill_tree_repository
    
    service = get_skill_tree_query_service()
    repo = get_skill_tree_repository()
    
    # STEP 1: Get actual node from DB to use its real name
    search_context = "Machine Learning"  # Default fallback
    
    try:
        # Try to parse node_id as UUID
        from uuid import UUID as parse_uuid
        try:
            # get_node_by_id expects string
            db_node = await repo.get_node_by_id(node_id)
            if db_node:
                search_context = db_node.name
                print(f"✅ Found node in DB: {db_node.name}")
        except Exception as e:
            print(f"⚠️ Error querying DB for node: {e}")
            
        # If still no context and session exists, use session title
        if search_context == "Machine Learning" and session_id:
            from modules.chat.infrastructure.repository import ChatRepositoryImpl
            chat_repo = ChatRepositoryImpl()
            session = await chat_repo.get_session(UUID(session_id))
            if session and session.title:
                search_context = session.title
    except Exception as e:
        print(f"⚠️ Error fetching node context: {e}")
    
    # STEP 2: Get existing node IDs from session to avoid duplicates
    existing_node_ids = []
    if session_id:
        try:
            from modules.chat.infrastructure.repository import ChatRepositoryImpl
            chat_repo = ChatRepositoryImpl()
            session = await chat_repo.get_session(UUID(session_id))
            if session and session.context_data:
                tree_nodes = session.context_data.get("tree_nodes", [])
                existing_node_ids = [n.get("id") for n in tree_nodes]
                print(f"  - Found {len(existing_node_ids)} existing nodes in session")
        except Exception as e:
            print(f"⚠️ Error fetching session context: {e}")

    print(f"\n🔍 [API] get_node_alternatives called:")
    print(f"  - node_id: {node_id}")
    print(f"  - level: {level}")
    print(f"  - search_context: {search_context}")
    
    # Pass existing IDs to exclude them from alternatives
    result = await service.find_alternatives(
        level, 
        search_context, 
        "", 
        existing_node_ids=existing_node_ids
    )
    print(f"  - result count: {len(result)}\n")
    return result

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
                        "original_node_id": node.id if hasattr(node, "id") and len(str(node.id)) > 20 else None, # Heuristic or check metadata
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
class SwapNodeRequest(BaseModel):
    original_node_id: str
    new_node: dict

@router.post("/session/{session_id}/swap")
async def swap_session_node(
    session_id: str,
    payload: SwapNodeRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Swap a node in the session's skill tree with a new one.
    Removes descendants of the swapped node to ensure consistency.
    """
    from modules.skill_tree.domain.services.skill_tree_swap import get_skill_tree_swap_service
    service = get_skill_tree_swap_service()
    
    updated_tree = await service.swap_node(UUID(session_id), payload.original_node_id, payload.new_node)
    
    if updated_tree is None:
        raise HTTPException(status_code=400, detail="Failed to swap node: Node not found or session invalid")
        
    return {"status": "success", "nodes": updated_tree}


# =============== MY SKILL TREE ENDPOINTS ===============

class SaveToMyTreeRequest(BaseModel):
    session_id: str
    node_ids: List[str]

@router.get("/my-tree")
async def get_my_tree(
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Get the user's personal skill tree with all saved nodes.
    """
    repo = get_skill_tree_repository()
    tree_data = await repo.get_full_user_tree(user_id)
    
    if tree_data is None:
        # Return empty tree structure instead of None
        return {"id": None, "name": "My Learning Path", "nodes": [], "edges": []}
    
    return tree_data


@router.post("/my-tree/save")
async def save_to_my_tree(
    request: SaveToMyTreeRequest,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Save nodes from a chat session to user's personal skill tree.
    """
    # Get nodes from session context
    try:
        from modules.chat.infrastructure.repository import ChatRepositoryImpl
        chat_repo = ChatRepositoryImpl()
        session = await chat_repo.get_session(UUID(request.session_id))
        
        if not session or not session.context_data:
            raise HTTPException(status_code=404, detail="Session not found or has no tree data")
        
        tree_nodes = session.context_data.get("tree_nodes", [])
        if not tree_nodes:
            raise HTTPException(status_code=400, detail="No tree nodes in session")
        
        # Filter to requested node_ids (or all if empty)
        if request.node_ids:
            node_data = [n for n in tree_nodes if n.get("id") in request.node_ids]
        else:
            node_data = tree_nodes
        
        if not node_data:
            raise HTTPException(status_code=400, detail="No matching nodes found")
        
        # Save to user's tree
        repo = get_skill_tree_repository()
        result = await repo.add_nodes_to_user_tree(user_id, request.session_id, node_data)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"⚠️ Error saving to my tree: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


@router.delete("/my-tree/nodes/{node_id}")
async def remove_from_my_tree(
    node_id: str,
    user_id: UUID = Depends(get_current_user_id)
):
    """
    Remove a node from user's personal skill tree.
    """
    repo = get_skill_tree_repository()
    success = await repo.remove_node_from_user_tree(user_id, node_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Node not found or does not belong to user")
    
    return {"status": "success", "message": "Node removed"}

