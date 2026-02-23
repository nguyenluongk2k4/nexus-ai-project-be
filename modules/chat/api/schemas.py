# Chat Module - API Schemas

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request for sending a chat message"""
    text: str
    session_id: Optional[str] = None
    attachments: list[dict] = []


class ChatMessageResponse(BaseModel):
    """Response from chat message"""
    session_id: str
    user_message: str
    bot_response: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """Response for chat session info"""
    id: str
    title: Optional[str] = None
    context_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Response for a single message"""
    id: str
    role: str
    content: str
    attachments: list[dict] = []
    created_at: datetime


class AsyncChatRequest(BaseModel):
    """Async chat request (for 202 Accepted response)"""
    text: str
    session_id: Optional[str] = None
    attachments: list[dict] = []


class AsyncChatAcceptedResponse(BaseModel):
    """202 Accepted response for async chat processing"""
    request_id: str
    session_id: str
    task_id: str
    status: str = "processing"
    message: str = "Your message is being processed. Listen to /ws/chat/{session_id} for updates."


class ChatEventPayload(BaseModel):
    """Redis Pub/Sub event payload"""
    session_id: int
    type: str  # intent_detected, rendering_progress, tree_ready, error
    timestamp: Optional[datetime] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    tree: Optional[dict] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
