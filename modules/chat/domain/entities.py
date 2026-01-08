# Chat Module - Domain Entities

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum


class MessageRole(str, Enum):
    """Role of message sender"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """A single chat message"""
    session_id: UUID
    role: MessageRole
    content: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    """A chat session containing messages"""
    id: UUID = field(default_factory=uuid4)
    user_id: Optional[UUID] = None
    title: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
