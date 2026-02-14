# Chat Module - Repository Implementation

from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select


from modules.chat.domain.entities import ChatSession, Message, MessageRole
from modules.chat.domain.ports import ChatRepositoryPort
from modules.chat.infrastructure.models import ChatSessionModel, MessageModel
from shared.database.connection import async_session_maker


def _to_uuid(value) -> UUID:
    """Safely convert value to UUID"""
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class ChatRepositoryImpl(ChatRepositoryPort):
    """SQLAlchemy implementation of ChatRepositoryPort"""
    
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        """Get chat session by ID"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(ChatSessionModel).where(ChatSessionModel.id == session_id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return ChatSession(
                id=_to_uuid(model.id),
                user_id=_to_uuid(model.user_id) if model.user_id else None,
                title=model.title,
                context_data=model.context_data,
                created_at=model.created_at,
                updated_at=model.updated_at
            )
    
    async def update_session_context(self, session_id: UUID, context_data: dict) -> bool:
        """Update session context data (e.g. skill tree)"""
        async with async_session_maker() as db:
            from sqlalchemy import update
            stmt = (
                update(ChatSessionModel)
                .where(ChatSessionModel.id == session_id)
                .values(context_data=context_data)
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0
    
    async def update_session_status(self, session_id: UUID, status: str = 'idle', request_id: str = None) -> bool:
        """Update session status and request_id"""
        async with async_session_maker() as db:
            from sqlalchemy import update
            from datetime import datetime
            
            values = {
                'status': status,
                'updated_at': datetime.utcnow()
            }
            if request_id:
                values['request_id'] = request_id
            
            stmt = (
                update(ChatSessionModel)
                .where(ChatSessionModel.id == session_id)
                .values(**values)
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0
    
    
    async def get_user_sessions(self, user_id: UUID) -> List[ChatSession]:
        """Get all sessions for a user"""
        async with async_session_maker() as db:
            result = await db.execute(
                select(ChatSessionModel)
                .where(ChatSessionModel.user_id == user_id)
                .order_by(ChatSessionModel.updated_at.desc())
            )
            models = result.scalars().all()
            
            return [
                ChatSession(
                    id=_to_uuid(m.id),
                    user_id=_to_uuid(m.user_id) if m.user_id else None,
                    title=m.title,
                    context_data=m.context_data,
                    created_at=m.created_at,
                    updated_at=m.updated_at
                )
                for m in models
            ]
    
    async def create_session(self, session: ChatSession) -> ChatSession:
        """Create new chat session"""
        async with async_session_maker() as db:
            model = ChatSessionModel(
                id=session.id if session.id else uuid4(),
                user_id=session.user_id if session.user_id else None,
                title=session.title
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
            
            return ChatSession(
                id=_to_uuid(model.id),
                user_id=_to_uuid(model.user_id) if model.user_id else None,
                title=model.title,
                created_at=model.created_at,
                updated_at=model.updated_at
            )
    
    async def add_message(self, message: Message) -> Message:
        """Add message to session"""
        async with async_session_maker() as db:
            model = MessageModel(
                id=message.id if message.id else uuid4(),
                session_id=message.session_id,
                role=message.role.value if isinstance(message.role, MessageRole) else message.role,
                content=message.content,
                attachments=message.attachments # Added attachments
            )
            db.add(model)
            await db.commit()
            await db.refresh(model)
            
            return Message(
                id=_to_uuid(model.id),
                session_id=_to_uuid(model.session_id),
                role=MessageRole(model.role),
                content=model.content,
                attachments=model.attachments or [], # Added attachments
                created_at=model.created_at
            )
    
    async def get_session_messages(self, session_id: UUID, limit: int = 50) -> List[Message]:
        """Get messages for session"""
        async with async_session_maker() as db:
            # Direct UUID comparison
            result = await db.execute(
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.created_at.desc())
                .limit(limit)
            )
            models = result.scalars().all()
            
            # Reverse to get chronological order
            messages = [
                Message(
                    id=_to_uuid(m.id),
                    session_id=_to_uuid(m.session_id),
                    role=MessageRole(m.role),
                    content=m.content,
                    attachments=m.attachments or [], # Added attachments
                    created_at=m.created_at
                )
                for m in reversed(models)
            ]
            
            return messages
    
    async def get_recent_sessions(self, limit: int = 5, offset: int = 0, user_id: UUID = None) -> List[ChatSession]:
        """Get recent sessions with pagination for load more"""
        async with async_session_maker() as db:
            stmt = select(ChatSessionModel).order_by(ChatSessionModel.updated_at.desc())
            
            if user_id:
                stmt = stmt.where(ChatSessionModel.user_id == user_id)
            
            result = await db.execute(
                stmt.offset(offset).limit(limit)
            )
            models = result.scalars().all()
            
            return [
                ChatSession(
                    id=_to_uuid(m.id),
                    user_id=_to_uuid(m.user_id) if m.user_id else None,
                    title=m.title,
                    context_data=m.context_data,
                    created_at=m.created_at,
                    updated_at=m.updated_at
                )
                for m in models
            ]
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and its messages"""
        async with async_session_maker() as db:
            # Delete messages first
            from sqlalchemy import delete
            await db.execute(
                delete(MessageModel).where(MessageModel.session_id == session_id)
            )
            
            # Delete session
            result = await db.execute(
                delete(ChatSessionModel).where(ChatSessionModel.id == session_id)
            )
            await db.commit()
            
            return result.rowcount > 0
