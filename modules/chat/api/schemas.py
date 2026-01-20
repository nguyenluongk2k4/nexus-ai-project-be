# Chat Module - API Schemas

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request for sending a chat message"""
    text: str
    session_id: Optional[str] = None


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
    created_at: datetime
