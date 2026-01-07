# Chat API Endpoints
# WebSocket and HTTP endpoints for AI chat

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
import json

from app.schemas import ChatMessageRequest, ChatMessageResponse, ChatSessionResponse
from app.deps import get_chatbot_service, get_llm, get_vector_store

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
async def send_message(
    data: ChatMessageRequest,
    llm = Depends(get_llm),
    vector_store = Depends(get_vector_store)
):
    """
    Gửi tin nhắn cho AI và nhận câu trả lời.
    - Sử dụng RAG để tìm context phù hợp
    - Gemini AI để generate response
    """
    from datetime import datetime
    from uuid import uuid4
    
    # Search relevant context from ChromaDB
    context_docs = vector_store.search(data.text, n_results=3)
    
    # Build prompt with context
    context = "\n".join([f"- {doc[:300]}" for doc in context_docs])
    prompt = f"""Dựa trên thông tin sau:
{context}

Câu hỏi: {data.text}

Trả lời ngắn gọn, có cấu trúc:"""
    
    # Generate response
    response = await llm.generate(prompt)
    
    session_id = data.session_id or str(uuid4())
    
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
    # TODO: Implement with database
    return []


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket
):
    """
    WebSocket endpoint cho real-time chat.
    
    Protocol:
    - Client gửi: {"type": "user_message", "text": "...", "session_id": "..."}
    - Server trả: {"type": "bot_message", "text": "...", "session_id": "..."}
    """
    await websocket.accept()
    
    # Get services
    llm = get_llm()
    vector_store = get_vector_store()
    
    try:
        while True:
            # Receive message
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
                
                # Create session if needed
                if not session_id:
                    from uuid import uuid4
                    session_id = str(uuid4())
                    await websocket.send_text(json.dumps({
                        "type": "session_started",
                        "session_id": session_id
                    }))
                
                # Send thinking status
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "thinking",
                    "session_id": session_id
                }))
                
                try:
                    # Search context
                    context_docs = vector_store.search(text, n_results=3)
                    context = "\n".join([f"- {doc[:300]}" for doc in context_docs])
                    
                    # Build prompt
                    prompt = f"""Dựa trên thông tin sau:
{context}

Câu hỏi: {text}

Trả lời ngắn gọn, có cấu trúc:"""
                    
                    # Generate response
                    response = await llm.generate(prompt)
                    
                    # Send response
                    await websocket.send_text(json.dumps({
                        "type": "bot_message",
                        "text": response,
                        "session_id": session_id
                    }))
                    
                except Exception as e:
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
