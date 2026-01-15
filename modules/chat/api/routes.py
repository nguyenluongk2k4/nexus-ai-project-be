# Chat Module - API Routes
# HTTP and WebSocket endpoints for AI chat

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import logging
from uuid import UUID

from modules.chat.api.schemas import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from modules.chat.providers import get_chatbot_service
from modules.auth.providers import get_jwt_service, get_user_repository
from modules.auth.api.deps import get_current_user_id

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Security scheme
security = HTTPBearer()





# ============================================================
# HTTP ENDPOINTS
# ============================================================

@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Gửi tin nhắn cho AI",
    description="Gửi tin nhắn và nhận phản hồi từ AI chatbot (RAG-enhanced)"
)
async def send_message(data: ChatMessageRequest):
    """
    Gửi tin nhắn cho AI và nhận câu trả lời.
    Sử dụng ChatbotService (DDD layer separation)
    """
    from datetime import datetime
    from uuid import uuid4, UUID
    from modules.chat.domain.entities import ChatSession
    
    # Get service
    chatbot = get_chatbot_service()
    
    # Create session if needed
    session_id = data.session_id or str(uuid4())
    
    if not data.session_id:
        new_session = ChatSession(id=UUID(session_id), title=data.text[:50])
        await chatbot.chat_repo.create_session(new_session)
    
    # Use ChatbotService
    try:
        response = await chatbot.respond(UUID(session_id), data.text)
        logger.info(f"✅ Processed message for session: {session_id}")
    except Exception as e:
        logger.error(f"❌ ChatbotService error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return ChatMessageResponse(
        session_id=session_id,
        user_message=data.text,
        bot_response=response,
        created_at=datetime.now()
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="Lấy danh sách chat sessions"
)
async def list_sessions(limit: int = 5, offset: int = 0, user_id: UUID = Depends(get_current_user_id)):
    """Lấy danh sách chat sessions với pagination (load more)"""
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    sessions = await repo.get_recent_sessions(limit=limit, offset=offset, user_id=user_id)
    
    return [
        ChatSessionResponse(
            id=str(s.id),
            title=s.title,
            context_data=s.context_data,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list,
    summary="Lấy tin nhắn của session"
)
async def get_session_messages(session_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Lấy tất cả tin nhắn của một session"""
    from uuid import UUID
    from modules.chat.api.schemas import MessageResponse
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    messages = await repo.get_session_messages(UUID(session_id))
    
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role.value,
            content=m.content,
            created_at=m.created_at
        )
        for m in messages
    ]


@router.delete(
    "/sessions/{session_id}",
    summary="Xóa chat session"
)
async def delete_session(session_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Xóa session và tất cả tin nhắn của nó"""
    from uuid import UUID
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    deleted = await repo.delete_session(UUID(session_id))
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with support for:
    - User authentication (via token)
    - Session management
    - Skill Tree generation and persistence
    - Robust error handling
    """
    await websocket.accept()
    
    # Get ChatbotService
    try:
        chatbot = get_chatbot_service()
    except Exception as e:
        logger.error(f"❌ [WS] Failed to get ChatbotService: {e}")
        await websocket.close(code=1011)
        return
    
    try:
        while True:
            try:
                raw_msg = await websocket.receive_text()
                
                try:
                    data = json.loads(raw_msg)
                except:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "invalid_json",
                        "message": "Message must be valid JSON"
                    }))
                    continue
                
                msg_type = data.get("type")
                session_id = data.get("session_id")
                
                # Handle ping
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue
                
                # Handle new session
                if msg_type == "new_session":
                    from uuid import uuid4
                    session_id = str(uuid4())
                    await websocket.send_text(json.dumps({
                        "type": "session_started",
                        "session_id": session_id
                    }))
                    continue
                
                # Handle user message
                if msg_type == "user_message":
                    text = (data.get("text") or "").strip()
                    
                    if not text:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "empty_text",
                            "message": "Text cannot be empty"
                        }))
                        continue
                    
                    from uuid import uuid4, UUID
                    from modules.chat.domain.entities import ChatSession
                    
                    # 1. User Identification
                    token = data.get("token")
                    user_id = None
                    if token:
                        try:
                            from modules.auth.providers import get_jwt_service
                            jwt_service = get_jwt_service()
                            uid_str = jwt_service.get_user_id_from_token(token)
                            if uid_str:
                                user_id = UUID(uid_str)
                        except Exception as e:
                            logger.warning(f"⚠️ [WS] Invalid token: {e}")

                    # 2. Session Management
                    if not session_id:
                        session_id = str(uuid4())
                        new_session = ChatSession(
                            id=UUID(session_id), 
                            title=text[:50],
                            user_id=user_id
                        )
                        await chatbot.chat_repo.create_session(new_session)
                        
                        await websocket.send_text(json.dumps({
                            "type": "session_started",
                            "session_id": session_id
                        }))
                    else:
                        existing_session = await chatbot.chat_repo.get_session(UUID(session_id))
                        if not existing_session:
                            new_session = ChatSession(
                                id=UUID(session_id), 
                                title=text[:50],
                                user_id=user_id
                            )
                            await chatbot.chat_repo.create_session(new_session)
                            logger.info(f"✨ [WS] Created missing session: {session_id}")
                    
                    # 3. Status Update
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": "thinking",
                        "session_id": session_id
                    }))
                    
                    try:
                        # 4. Chat Processing
                        response = await chatbot.respond(UUID(session_id), text)
                        logger.info(f"✅ [WS] Processed message for {session_id}")
                        
                        await websocket.send_text(json.dumps({
                            "type": "bot_message",
                            "text": response,
                            "session_id": session_id
                        }))
                        
                        # 5. Skill Tree Generation (Re-enabled)
                        # Analyze chat and generate/update tree based on learning intent
                        try:
                            import time
                            start_time = time.time()
                            
                            from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
                            skill_tree_service = get_skill_tree_query_service()
                            
                            # Check if this is a skill tree related query
                            logger.info(f"🔍 [WS] Checking if skill tree query...")
                            is_tree_query = await skill_tree_service.is_skill_tree_query(text)
                            logger.info(f"🔍 [WS] Is tree query: {is_tree_query} (took {time.time()-start_time:.2f}s)")
                            
                            if is_tree_query:
                                logger.info(f"🎯 [WS] Detected skill tree query, generating tree...")
                                
                                # Notify frontend that tree is loading
                                await websocket.send_text(json.dumps({
                                    "type": "tree_loading",
                                    "session_id": session_id
                                }))
                                
                                # Generate tree nodes based on the query
                                gen_start = time.time()
                                tree_nodes = await skill_tree_service.query(text)
                                logger.info(f"⏱️ [WS] Tree generation took {time.time()-gen_start:.2f}s, got {len(tree_nodes) if tree_nodes else 0} nodes")
                                
                                if tree_nodes:
                                    # Build nodes data for frontend
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
                                    
                                    # Send tree nodes directly to frontend via WS
                                    await websocket.send_text(json.dumps({
                                        "type": "tree_nodes",
                                        "session_id": session_id,
                                        "nodes": nodes_data
                                    }))
                                    logger.info(f"✅ [WS] Sent {len(nodes_data)} generated tree nodes")
                                    
                                    # Also persist tree to session context for API retrieval
                                    try:
                                        await chatbot.chat_repo.update_session_context(
                                            UUID(session_id), 
                                            {"tree_nodes": nodes_data}
                                        )
                                        logger.info(f"💾 [WS] Saved tree to session context")
                                    except Exception as save_err:
                                        logger.warning(f"⚠️ [WS] Could not save tree to context: {save_err}")
                                else:
                                    logger.warning(f"⚠️ [WS] Tree generation returned empty/null")
                                    
                        except Exception as tree_err:
                            import traceback
                            logger.error(f"⚠️ [WS] Tree generation error (non-fatal): {tree_err}")
                            logger.error(f"⚠️ [WS] Traceback: {traceback.format_exc()}")

                        
                    except Exception as inference_err:
                        logger.error(f"❌ [WS] Inference Error: {inference_err}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "inference_failed",
                            "message": str(inference_err),
                            "session_id": session_id
                        }))
                    
                    # 6. Status Update (Idle)
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": "idle",
                        "session_id": session_id
                    }))
                    continue

                # Unknown type
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "unknown_type",
                    "message": f"Unknown message type: {msg_type}"
                }))

            except Exception as loop_err:
                logger.error(f"❌ [WS] Loop Error: {loop_err}", exc_info=True)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "internal_error",
                    "message": "Server internal error"
                }))
                continue
    
    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as fatal_err:
        logger.critical(f"❌ [WS] Fatal Connection Error: {fatal_err}", exc_info=True)
