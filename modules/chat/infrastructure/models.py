# Chat Module - Database Models

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import uuid as uuid_module

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.connection import Base


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Note: user_id FK removed temporarily - users table not in new module structure yet
    user_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    context_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="idle")  # idle, rendering
    request_id: Mapped[Optional[uuid_module.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    messages: Mapped[List["MessageModel"]] = relationship(back_populates="session", order_by="MessageModel.created_at")


class MessageModel(Base):
    __tablename__ = "messages"
    
    id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[uuid_module.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    session: Mapped["ChatSessionModel"] = relationship(back_populates="messages")
