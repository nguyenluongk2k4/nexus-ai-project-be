# Chat Module - API Routes
# HTTP and WebSocket endpoints for AI chat

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import json
import logging

from modules.chat.api.schemas import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from modules.chat.providers import get_chatbot_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


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
async def list_sessions():
    """Lấy danh sách chat sessions của user hiện tại"""
    # TODO: Implement with user authentication
    return []


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint cho real-time chat.
    
    Protocol:
    - Client gửi: {"type": "user_message", "text": "...", "session_id": "..."}
    - Server trả: {"type": "bot_message", "text": "...", "session_id": "..."}
    """
    await websocket.accept()
    
    # Get ChatbotService
    chatbot = get_chatbot_service()
    
    try:
        while True:
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
                
                # Create or verify session exists
                if not session_id:
                    # No session ID - create new session
                    session_id = str(uuid4())
                    new_session = ChatSession(id=UUID(session_id), title=text[:50])
                    await chatbot.chat_repo.create_session(new_session)
                    
                    await websocket.send_text(json.dumps({
                        "type": "session_started",
                        "session_id": session_id
                    }))
                else:
                    # Session ID provided - check if exists in DB
                    existing_session = await chatbot.chat_repo.get_session(UUID(session_id))
                    if not existing_session:
                        # Session doesn't exist - create it
                        new_session = ChatSession(id=UUID(session_id), title=text[:50])
                        await chatbot.chat_repo.create_session(new_session)
                        logger.info(f"Created missing session: {session_id}")
                
                # Send thinking status
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "thinking",
                    "session_id": session_id
                }))
                
                try:
                    response = await chatbot.respond(UUID(session_id), text)
                    logger.info(f"✅ WS: Processed message for session: {session_id}")
                    
                    await websocket.send_text(json.dumps({
                        "type": "bot_message",
                        "text": response,
                        "session_id": session_id
                    }))
                    
                except Exception as e:
                    logger.error(f"❌ WS ChatbotService error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "inference_failed",
                        "message": str(e),
                        "session_id": session_id
                    }))
                
                # Send idle status
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "idle",
                    "session_id": session_id
                }))
                continue
            
            # Unknown message type
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": "unknown_type",
                "message": f"Unknown message type: {msg_type}"
            }))
    
    except WebSocketDisconnect:
        pass
