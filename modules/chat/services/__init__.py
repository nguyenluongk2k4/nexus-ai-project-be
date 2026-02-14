# Chat Processor Service
# Handles async chat request processing

import logging
from uuid import UUID, uuid4
from typing import Optional
from config.celery_config import celery_app
from services.redis.event_manager import redis_event_manager
from config.settings import settings

logger = logging.getLogger(__name__)


class ChatProcessorService:
    """
    Service to handle async chat processing
    - Generate and track request_id
    - Enqueue Celery task
    - Publish intent event to Redis
    """
    
    @staticmethod
    async def process_chat_message(
        session_id: UUID,
        user_message: str,
        user_id: Optional[UUID] = None,
        attachments: Optional[list] = None
    ) -> dict:
        """
        Process incoming chat message asynchronously
        
        Args:
            session_id: Chat session UUID
            user_message: User's text message
            user_id: User ID (optional)
            attachments: List of attachments (optional)
        
        Returns:
            {
                "request_id": str (UUID),
                "session_id": str,
                "status": "processing"
            }
        """
        try:
            # Generate request_id for tracking
            request_id = str(uuid4())
            
            logger.info(f"📨 Processing chat message: session={session_id}, request={request_id}")
            
            # Update session status in database (will do in task or update here)
            # For now, just prepare the event
            
            # Publish intent event to Redis
            await redis_event_manager.publish_intent_event(
                session_id=int(str(session_id).replace('-', '')[:8], 16) % (2**31),  # Convert UUID to session ID
                user_message=user_message,
                request_id=request_id
            )
            
            logger.info(f"✅ Intent event published: {request_id}")
            
            # Enqueue Celery task for async processing
            from modules.chat.tasks import process_chat_intent
            
            task = process_chat_intent.delay(
                session_id=str(session_id),
                user_message=user_message,
                request_id=request_id,
                user_id=str(user_id) if user_id else None,
                attachments=attachments or []
            )
            
            logger.info(f"🎯 Celery task enqueued: {task.id}")
            
            return {
                "request_id": request_id,
                "session_id": str(session_id),
                "task_id": task.id,
                "status": "processing"
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to process chat message: {e}", exc_info=True)
            raise
