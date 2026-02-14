# Chat Module - Celery Tasks
# Background tasks for async chat processing

import logging
import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from config.celery_config import celery_app
from services.redis.event_manager import redis_event_manager
from config.settings import settings
from modules.chat.services.gemini_intent_service import GeminiIntentService
from modules.chat.services.rag_service import RAGService
from modules.chat.services.tree_renderer_service import TreeRenderService
from modules.chat.infrastructure.repository import ChatRepositoryImpl
from sqlalchemy import update
from modules.chat.infrastructure.models import ChatSessionModel
from shared.database.connection import async_session_maker
from celery.signals import worker_ready, worker_process_init

logger = logging.getLogger(__name__)

# Global cache for pre-loaded services (per worker process)
_worker_cache = {
    "rag_service": None,
    "tree_service": None,
    "initialized": False
}


def _init_worker_cache():
    """Initialize cached services in this worker process"""
    global _worker_cache
    
    if _worker_cache["initialized"]:
        return  # Already initialized
    
    logger.info("\n⏳ Initializing worker cache: Loading RAG service...")
    
    try:
        # Pre-load RAG service
        _worker_cache["rag_service"] = RAGService()
        logger.info("✅ RAG service loaded: Embedding model cached in this worker")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load RAG service: {e}")
    
    try:
        # Pre-load Tree service
        _worker_cache["tree_service"] = TreeRenderService()
        logger.info("✅ Tree service loaded in this worker")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load Tree service: {e}")
    
    _worker_cache["initialized"] = True
    logger.info("🎯 Worker cache ready!\n")


@worker_process_init.connect
def setup_worker_process(sender, **kwargs):
    """Initialize cache when worker process starts (runs in each child worker)"""
    logger.info("\n🚀 Worker process starting - Pre-loading services...")
    _init_worker_cache()


@worker_ready.connect
def setup_worker_startup(sender, **kwargs):
    """Log main worker ready (runs once in MainProcess)"""
    logger.info("🎯 NexusAI Celery Worker - All processes ready!")


@celery_app.task(
    bind=True,
    retry_kwargs={"max_retries": 3},
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    task_track_started=True,
    queue="chat_intent"
)
def process_chat_intent(
    self,
    session_id: str,
    user_message: str,
    request_id: str,
    user_id: Optional[str] = None,
    attachments: Optional[List] = None
) -> dict:
    """
    Process chat intent with Gemini + RAG + Tree rendering
    
    Flow:
    1. Update session status to 'rendering'
    2. Publish rendering_started event
    3. Extract intent via Gemini
    4. Query RAG for documents
    5. Render skill tree
    6. Update session with tree data
    7. Publish tree_ready event
    8. Reset status to 'idle'
    
    Args:
        session_id: Chat session UUID (as string)
        user_message: User's text message
        request_id: Request tracking UUID
        user_id: User ID (optional)
        attachments: List of attachments (optional)
    
    Returns:
        {
            "request_id": str,
            "session_id": str,
            "status": "completed|failed",
            "tree": dict (if success),
            "error": str (if failed)
        }
    """
    # Fix: Create event loop with proper cleanup
    try:
        # Check if event loop exists and is closed
        loop = None
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're already in an async context - use it directly
            logger.warning("⚠️ Event loop already running - using existing loop")
            return asyncio.run_coroutine_threadsafe(
                _process_chat_intent_async(
                    session_id=session_id,
                    user_message=user_message,
                    request_id=request_id,
                    user_id=user_id,
                    attachments=attachments or []
                ),
                loop
            ).result()
        except RuntimeError:
            # No running loop, we're in sync context (normal Celery case)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    _process_chat_intent_async(
                        session_id=session_id,
                        user_message=user_message,
                        request_id=request_id,
                        user_id=user_id,
                        attachments=attachments or []
                    )
                )
                return result
            finally:
                # Properly cleanup event loop
                loop.close()
                asyncio.set_event_loop(None)
    except Exception as e:
        logger.error(f"❌ Fatal error in process_chat_intent: {e}", exc_info=True)
        return {
            "request_id": request_id,
            "session_id": session_id,
            "status": "failed",
            "error": f"Fatal error: {str(e)}"
        }


async def _process_chat_intent_async(
    session_id: str,
    user_message: str,
    request_id: str,
    user_id: Optional[str] = None,
    attachments: Optional[List] = None
) -> dict:
    """Async implementation of chat processing"""
    global _worker_cache
    
    session_uuid = None
    
    try:
        # Initialize worker cache on first task (lazy load)
        _init_worker_cache()
        
        session_uuid = int(session_id.replace('-', '')[:8], 16) % (2**31)
        attachments = attachments or []
        session_uuid_obj = UUID(session_id)
        
        logger.info(f"🚀 Starting chat intent processing: {request_id}")
        
        # Use cached services from this worker
        intent_service = GeminiIntentService()
        rag_service = _worker_cache["rag_service"] or RAGService()
        tree_service = _worker_cache["tree_service"] or TreeRenderService()
        chat_repo = ChatRepositoryImpl()
        
        # Step 1: Update session status to 'rendering'
        logger.info(f"📝 Step 1: Updating session status to 'rendering'")
        try:
            await _update_session_status(session_uuid_obj, "rendering")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update session status: {e}")
        
        # Step 2: Publish rendering_started event (~10% progress)
        logger.info(f"📢 Step 2: Publishing rendering_started event (10%)")
        try:
            await redis_event_manager.publish_rendering_event(
                session_id=session_uuid,
                progress=10,
                status="rendering",
                step="intent_extraction"
            )
            # Cache progress
            await _cache_progress(session_id, 10, "rendering", "Extracting intent...")
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish progress event: {e}")
        
        # Step 3: Extract intent via Gemini
        logger.info(f"🧠 Step 3: Extracting intent via Gemini")
        intent = "general"
        keywords = []
        try:
            logger.info(f"   → Calling Gemini API for intent detection...")
            intent_result = await intent_service.extract_intent(user_message)
            intent = intent_result.get("intent", "general")
            keywords = intent_result.get("keywords", [])
            logger.info(f"✅ Intent extracted: {intent}, keywords: {keywords}")
        except asyncio.TimeoutError:
            logger.error(f"❌ Intent extraction TIMEOUT - using default")
        except Exception as e:
            logger.error(f"❌ Intent extraction failed: {e}", exc_info=True)
        
        # Step 4: Query RAG for documents (~40% progress)
        logger.info(f"📚 Step 4: Querying RAG for documents")
        try:
            await redis_event_manager.publish_rendering_event(
                session_id=session_uuid,
                progress=40,
                status="rendering",
                step="rag_query"
            )
            # Cache progress
            await _cache_progress(session_id, 40, "rendering", "Querying documents...")
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish progress event: {e}")
        
        try:
            logger.info(f"   → Querying RAG for documents...")
            documents = await rag_service.query_documents(
                query=user_message,
                n_results=5
            )
            logger.info(f"✅ Found {len(documents)} documents from RAG")
        except asyncio.TimeoutError:
            logger.error(f"❌ RAG query TIMEOUT")
            documents = []
        except Exception as e:
            logger.error(f"❌ RAG query failed: {e}", exc_info=True)
            documents = []
        
        # Step 5: Render skill tree (~70% progress)
        logger.info(f"🌳 Step 5: Rendering skill tree")
        try:
            await redis_event_manager.publish_rendering_event(
                session_id=session_uuid,
                progress=70,
                status="rendering",
                step="tree_rendering"
            )
            # Cache progress
            await _cache_progress(session_id, 70, "rendering", "Rendering tree...")
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish progress event: {e}")
        
        try:
            logger.info(f"   → Rendering tree with intent: {intent}")
            user_uuid = UUID(user_id) if user_id else None
            tree_data = await tree_service.render_tree(
                intent=intent,
                documents=documents,
                user_id=user_uuid
            )
            logger.info(f"✅ Tree rendered with {len(tree_data.get('nodes', []))} nodes")
        except asyncio.TimeoutError:
            logger.error(f"❌ Tree rendering TIMEOUT")
            tree_data = tree_service._default_tree(intent)
        except Exception as e:
            logger.error(f"❌ Tree rendering failed: {e}", exc_info=True)
            tree_data = tree_service._default_tree(intent)
        
        # Step 6: Store tree data and update session
        logger.info(f"💾 Step 6: Storing tree data")
        try:
            logger.info(f"   → Preparing context data...")
            # Transform nodes: convert 'label' field to 'name' for backend usecase compatibility
            raw_nodes = tree_data.get("nodes", []) if isinstance(tree_data, dict) else []
            transformed_nodes = []
            for node in raw_nodes:
                transformed_node = dict(node)  # Copy original node
                if "label" in transformed_node and "name" not in transformed_node:
                    transformed_node["name"] = transformed_node.pop("label")
                # Ensure all required fields exist
                if "type" not in transformed_node:
                    transformed_node["type"] = "skill"
                if "level" not in transformed_node:
                    transformed_node["level"] = 1
                if "description" not in transformed_node:
                    transformed_node["description"] = ""
                if "metadata" not in transformed_node:
                    transformed_node["metadata"] = {}
                transformed_nodes.append(transformed_node)
            
            # Format: save tree_nodes as the primary data structure
            context_data = {
                "tree_nodes": transformed_nodes,
                "tree": tree_data,  # Keep full tree for reference
                "intent": intent,
                "keywords": keywords,
                "documents_count": len(documents),
                "generated_at": datetime.utcnow().isoformat()
            }
            logger.info(f"   → Updating session context with {len(context_data.get('tree_nodes', []))} nodes...")
            await chat_repo.update_session_context(session_uuid_obj, context_data)
            logger.info(f"✅ Context data saved successfully: {len(context_data.get('tree_nodes', []))} nodes with transformed fields")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save context data: {e}", exc_info=True)
        
        # Step 7: Publish tree_ready event (100%)
        logger.info(f"✅ Step 7: Publishing tree_ready event (100%)")
        try:
            await redis_event_manager.publish_ready_event(
                session_id=session_uuid,
                tree_data=tree_data
            )
            # Cache final progress
            await _cache_progress(session_id, 100, "idle", "Complete!", tree_data)
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish tree_ready event: {e}")
        
        # Step 8: Reset session status to 'idle'
        logger.info(f"🔄 Step 8: Resetting status to idle")
        try:
            await _update_session_status(session_uuid_obj, "idle")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update session status to idle: {e}")
        
        return {
            "request_id": request_id,
            "session_id": session_id,
            "status": "completed",
            "intent": intent,
            "tree": tree_data
        }
    
    except Exception as e:
        logger.error(f"❌ Chat intent processing failed: {e}", exc_info=True)
        
        # Publish error event
        try:
            if session_uuid:
                await redis_event_manager.publish_error_event(
                    session_id=session_uuid,
                    error_message=str(e),
                    error_type="processing_error"
                )
                # Cache error state
                await _cache_progress(session_id, 0, "error", f"Error: {str(e)[:100]}")
        except Exception as pub_error:
            logger.warning(f"⚠️ Failed to publish error event: {pub_error}")
        
        # Reset session status to idle on error
        try:
            if session_uuid:
                await _update_session_status(UUID(session_id), "idle")
        except Exception as update_error:
            logger.warning(f"⚠️ Failed to reset session status: {update_error}")
        
        return {
            "request_id": request_id,
            "session_id": session_id,
            "status": "failed",
            "error": str(e)
        }


async def _update_session_status(session_id: UUID, status: str) -> bool:
    """Update session status in database"""
    try:
        async with async_session_maker() as db:
            stmt = (
                update(ChatSessionModel)
                .where(ChatSessionModel.id == session_id)
                .values(status=status, updated_at=datetime.utcnow())
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to update session status: {e}")
        return False


async def _cache_progress(
    session_id: str,
    progress: int,
    status: str,
    step: str,
    tree_data: Optional[dict] = None
) -> None:
    """Cache current progress to Redis"""
    try:
        progress_data = {
            "session_id": session_id,
            "progress": progress,
            "status": status,
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
            "tree": tree_data
        }
        
        import json
        key = f"chat:session:{session_id}:current_progress"
        value = json.dumps(progress_data)
        
        # Use asyncio to call sync Redis operation
        from services.redis.event_manager import redis_event_manager
        await redis_event_manager._set_cache(key, value, ttl=1800)
    except Exception as e:
        logger.warning(f"Failed to cache progress: {e}")
