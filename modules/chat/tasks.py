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
from modules.chat.infrastructure.repository import ChatRepositoryImpl
from sqlalchemy import update
from modules.chat.infrastructure.models import ChatSessionModel
from shared.database.connection import async_session_maker
from celery.signals import worker_ready, worker_process_init

logger = logging.getLogger(__name__)



def _convert_tree_nodes_to_dict(tree_nodes: List, intent: str) -> dict:
    """Convert List[TreeNodeResult] to tree dict format for frontend"""
    nodes = []
    
    for node in tree_nodes:
        nodes.append({
            "id": node.id,
            "icon": node.icon,
            "name": node.name,
            "type": node.type,
            "level": node.level,
            "filled": True,  # All nodes from SkillTreeQueryService are considered filled
            "metadata": node.metadata,
            "parentId": node.parent_id,
            "description": node.description or "",
            "original_node_id": getattr(node, "original_node_id", node.id)  # Use original ID if available
        })
    
    return {
        "tree_nodes": nodes
    }



# Global cache for pre-loaded services (per worker process)
_worker_cache = {
    "rag_service": None,
    "initialized": False
}


def _init_worker_cache():
    """Initialize cached services in this worker process"""
    global _worker_cache
    if _worker_cache["initialized"]:
        return
    logger.info("\n⏳ Initializing worker cache: Loading RAG service...")
    try:
        _worker_cache["rag_service"] = RAGService()
        logger.info("✅ RAG service loaded: Embedding model cached in this worker")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load RAG service: {e}")
    _worker_cache["initialized"] = True
    logger.info("🎯 Worker cache ready!\n")


# Persistent event loop for this worker process
# All async tasks reuse this loop → connections stay bound to same loop → no InterfaceError
_worker_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    """Get or create the persistent worker event loop"""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.info("🔄 Created new persistent event loop for worker")
    return _worker_loop


@worker_process_init.connect
def setup_worker_process(sender, **kwargs):
    """Initialize cache when worker process starts (runs in each child worker)"""
    logger.info("\n🚀 Worker process starting - Pre-loading services...")
    
    # Step 1: Create persistent event loop for this worker
    loop = _get_worker_loop()
    
    # Step 2: Dispose inherited engine to force fresh connections on this loop
    from shared.database.connection import engine
    
    # Pre-import all models so SQLAlchemy metadata can resolve cross-module Foreign Keys (e.g. users)
    import modules.auth.infrastructure.models
    import modules.coins.infrastructure.models
    import modules.chat.infrastructure.models
    import modules.skill_tree.infrastructure.models
    try:
        loop.run_until_complete(engine.dispose())
        logger.info("✅ Database engine disposed (clean connection pool for worker)")
    except Exception as e:
        logger.warning(f"⚠️ Failed to dispose engine: {e}")

    _init_worker_cache()
    logger.info("🎯 Worker process ready with persistent event loop!\n")


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
    attachments: Optional[List] = None,
    user_msg_id: Optional[str] = None
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
    try:
        # Reuse the persistent worker event loop
        loop = _get_worker_loop()
        
        result = loop.run_until_complete(
            _process_chat_intent_async(
                session_id=session_id,
                user_message=user_message,
                request_id=request_id,
                user_id=user_id,
                attachments=attachments or [],
                user_msg_id=user_msg_id
            )
        )
        return result
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
    attachments: Optional[List] = None,
    user_msg_id: Optional[str] = None
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
        rag_service = _worker_cache["rag_service"] or RAGService()
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
            
        # Check if it's a skill tree query
        from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
        skill_tree_service = get_skill_tree_query_service()
        
        # We need the AI response first to give full context for the tree query check
        logger.info(f"💬 Step 3.5: Generating AI Chatbot text response")
        try:
            from modules.chat.domain.services import ChatbotService
            from modules.chat.providers import get_llm, get_vector_store
            
            chat_service = ChatbotService(
                llm=get_llm(),
                vector_store=get_vector_store(),
                chat_repo=chat_repo
            )
            
            response_dict = await chat_service.respond(session_uuid_obj, user_message, attachments, user_msg_id=user_msg_id)
            ai_response = response_dict["text"]
            logger.info(f"✅ AI Response generated successfully")
            
            # Cache the response for the HTTP Stream to pick up without hammering the DB
            try:
                import json
                cache_key = f"chat:session:{session_id}:bot_message"
                await redis_event_manager.set_cache(cache_key, json.dumps(response_dict), ttl=600)
            except Exception as e:
                logger.warning(f"⚠️ Failed to cache bot_message: {e}")
                
        except Exception as e:
            logger.error(f"❌ AI Response generation failed: {e}", exc_info=True)
            ai_response = "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại sau."
        
        tree_context = f"{user_message}\n\nContext from AI: {ai_response[:2000]}"
        is_tree_query = await skill_tree_service.is_skill_tree_query(tree_context)
        
        if not is_tree_query:
            logger.info(f"⏭️ Not a skill tree query, skipping tree rendering.")
            # Set status to idle
            await _update_session_status(session_uuid_obj, "idle")
            await redis_event_manager.publish_ready_event(
                session_id=session_uuid,
                tree_data=None
            )
            return {
                "request_id": request_id,
                "session_id": session_id,
                "status": "completed",
                "intent": intent,
                "tree": None
            }
        
        else:
            logger.info(f"🌳 Skill tree query detected. Publishing tree_task_started event.")
            
            # Coin deduction moved to Step 4 before Chroma RAG
            
            channel = f"chat:session:{session_uuid}:reply"
            msg_data = {
                "type": "tree_task_started",
                "session_id": session_id,
                "request_id": request_id,
                "message": "Đang phân tích để tạo Skill Tree..."
            }
            await redis_event_manager.publish(channel, msg_data)
            
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
            # --- COINS DEDUCTION FOR TREE GENERATION ---
            if user_id:
                try:
                    from shared.database.connection import get_db_context
                    from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyCoinConfigRepository
                    from modules.coins.domain.services.coins_service import CoinsService
                    
                    async with get_db_context() as db:
                        coins_repo = SQLAlchemyCoinsRepository(db)
                        coins_service = CoinsService(coins_repo)
                        config_repo = SQLAlchemyCoinConfigRepository(db)
                        
                        coin_config_tree = await config_repo.get_config('generate_tree')
                        cost_tree = coin_config_tree.cost if coin_config_tree else 10
                        
                        # UUID parsing safely
                        uid = UUID(user_id) if isinstance(user_id, str) else user_id
                        
                        logger.info(f"💸💲 [DEDUCTION] Attempting to deduct {cost_tree} coins for {uid} immediately before Chroma...")
                        await coins_service.spend_coins(
                            user_id=uid,
                            amount=cost_tree,
                            service_type='skill_tree_generation',
                            description=f"Generated skill tree (from chat)"
                        )
                        logger.info(f"✅💲 [DEDUCTION] Successfully deducted {cost_tree} coins for tree generation!")
                        
                except ValueError as e:
                    logger.warning(f"🚫 Insufficient coins for tree generation for user {user_id}")
                    # Notify user via WS about insufficient coins
                    channel = f"chat:session:{session_uuid}:reply"
                    await redis_event_manager.publish(channel, {
                        "type": "error",
                        "error": "insufficient_coins",
                        "message": "Bạn không đủ xu để tạo skill tree. Hãy làm nhiệm vụ để nhận thêm xu!",
                        "session_id": session_id
                    })
                    # Reset status to idle so they can chat normally again
                    await _update_session_status(session_uuid_obj, "idle")
                    await redis_event_manager.publish_ready_event(session_id=session_uuid, tree_data=None)
                    return {
                        "request_id": request_id,
                        "session_id": session_id,
                        "status": "completed",
                        "intent": intent,
                        "tree": None
                    }
                except Exception as e:
                    logger.error(f"❌ Error deducting coins for tree generation: {e}")

            logger.info(f"   → Querying RAG/Chroma DB for documents...")
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
            logger.info(f"   → Rendering tree for message: {user_message}")
            
            from modules.skill_tree.domain.services.skill_tree_query import get_skill_tree_query_service
            skill_tree_service = get_skill_tree_query_service()
            
            tree_nodes = await skill_tree_service.query(user_message, max_level=None)
            
            if not tree_nodes:
                raise ValueError(f"No tree nodes generated for message: {user_message}")
            
            tree_data = _convert_tree_nodes_to_dict(tree_nodes, intent)
            logger.info(f"✅ Tree rendered with {len(tree_data.get('nodes', []))} nodes")
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"❌ Tree rendering failed: {e}", exc_info=True)
            raise
        
        
        # Step 6 & 8: Store tree data AND set status to idle (combined to avoid DB conflict)
        logger.info(f"💾 Step 6+8: Saving tree data and updating status to idle")
        try:
            # Store ONLY tree_nodes in context_data (Clean format)
            context_data = {
                "tree_nodes": tree_data.get("tree_nodes", [])
            }
            logger.info(f"   → Saving {len(context_data['tree_nodes'])} nodes + setting status=idle...")
            
            # Combined update to avoid asyncpg connection conflict
            await chat_repo.update_context_and_status(session_uuid_obj, context_data, status="idle")
            
            logger.info(f"✅ Tree data saved + status updated: {len(context_data['tree_nodes'])} nodes")
        except Exception as e:
            logger.error(f"❌ Failed to save tree + update status: {e}", exc_info=True)
            # Fallback: try updating status only
            try:
                await _update_session_status(session_uuid_obj, "idle")
            except Exception as e2:
                logger.warning(f"⚠️ Fallback status update also failed: {e2}")

        
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
