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
# Coins integration
from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.services.mission_service import MissionService
from shared.database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession

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
async def send_message(
    data: ChatMessageRequest, 
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
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
    
    # Coins Integration: Deduct 5 coins per message
    coins_repo = SQLAlchemyCoinsRepository(db)
    coins_service = CoinsService(coins_repo)
    
    try:
        await coins_service.spend_coins(
            user_id=UUID(user_id),
            amount=5,
            service_type='ai_chat',
            description=f"AI Chat: {data.text[:30]}"
        )
        
        # Update mission progress: AI Chat count
        mission_repo = SQLAlchemyMissionRepository(db)
        mission_service = MissionService(mission_repo, coins_service)
        await mission_service.update_progress(
            user_id=UUID(user_id),
            mission_type='ai_chat',
            progress_data={'increment': 1, 'field': 'count'}
        )
    except ValueError as e:
        raise HTTPException(status_code=402, detail="Bạn không đủ xu để sử dụng tính năng này. Hãy làm nhiệm vụ để nhận thêm xu!")

    # Use ChatbotService
    try:
        response = await chatbot.respond(UUID(session_id), data.text, data.attachments)
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
            attachments=m.attachments, # Added attachments
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
                        attachments = data.get("attachments", [])
                        
                        # 4.1 Coins & Missions Integration
                        skip_bot_response = False
                        if user_id:
                            # Use SQLAlchemy session from deps if possible, but the route doesn't have it as an argument
                            # We need to get a DB session here
                            from shared.database.connection import get_db
                            async for db in get_db():
                                try:
                                    # Coins Integration: Deduct 5 coins per message
                                    coins_repo = SQLAlchemyCoinsRepository(db)
                                    coins_service = CoinsService(coins_repo)
                                    
                                    await coins_service.spend_coins(
                                        user_id=user_id,
                                        amount=5,
                                        service_type='ai_chat',
                                        description=f"AI Chat (WS): {text[:30]}"
                                    )
                                    
                                    # Update mission progress: AI Chat count
                                    mission_repo = SQLAlchemyMissionRepository(db)
                                    mission_service = MissionService(mission_repo, coins_service)
                                    await mission_service.update_progress(
                                        user_id=user_id,
                                        mission_type='ai_chat',
                                        progress_data={'increment': 1, 'field': 'count'}
                                    )
                                    break # Success, exit session loop
                                except ValueError as e:
                                    await websocket.send_text(json.dumps({
                                        "type": "error",
                                        "error": "insufficient_coins",
                                        "message": "Bạn không đủ xu để sử dụng tính năng này. Hãy làm nhiệm vụ để nhận thêm xu!",
                                        "session_id": session_id
                                    }))
                                    skip_bot_response = True
                                    break # Exit DB session loop, but don't 'return' (keep WS alive)
                                except Exception as e:
                                    logger.error(f"❌ [WS] Deduct coins/mission error: {e}")
                                    # Non-fatal for the chat itself, but good to know
                                    break

                        if not skip_bot_response:
                            response = await chatbot.respond(UUID(session_id), text, attachments)
                            logger.info(f"✅ [WS] Processed message for {session_id}")
                            
                            await websocket.send_text(json.dumps({
                                "type": "bot_message",
                                "text": response,
                                "session_id": session_id
                            }))
                            
                            # 5. Skill Tree Signal - Let frontend call HTTP API to generate tree
                            # Only send signal that tree generation is possible, frontend will call HTTP
                            try:
                                from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
                                skill_tree_service = get_skill_tree_query_service()
                                
                                # Quick check if this is a skill tree related query
                                # Context-aware tree generation
                                # Combine user query with AI response (which contains file analysis)
                                # This allows "this job" queries to work because AI response has the details.
                                tree_context = f"{text}\n\nContext from AI: {response[:2000]}" # Limit context length
                                
                                is_tree_query = await skill_tree_service.is_skill_tree_query(tree_context)
                                
                                if is_tree_query:
                                    logger.info(f"🎯 [WS] Detected skill tree query, signaling frontend...")
                                    
                                    # Send signal to frontend to call HTTP streaming endpoint
                                    await websocket.send_text(json.dumps({
                                        "type": "tree_generating",
                                        "session_id": session_id,
                                        "message": tree_context  # Pass the RICH context for generation
                                    }))
                            except Exception as tree_err:
                                logger.error(f"⚠️ [WS] Tree check error (non-fatal): {tree_err}")

                        
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

            except WebSocketDisconnect:
                logger.info("[WS] Client disconnected in loop")
                break  # Exit loop cleanly on disconnect
            except Exception as loop_err:
                logger.error(f"❌ [WS] Loop Error: {loop_err}", exc_info=True)
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "internal_error",
                        "message": "Server internal error"
                    }))
                except Exception:
                    # Connection already closed, just break the loop
                    break
                continue
    
    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as fatal_err:
        logger.critical(f"❌ [WS] Fatal Connection Error: {fatal_err}", exc_info=True)
