# Chat Module - API Routes
# HTTP and WebSocket endpoints for AI chat

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import logging
from uuid import UUID, uuid4

from modules.chat.api.schemas import (
    ChatMessageRequest, ChatMessageResponse, ChatSessionResponse,
    AsyncChatRequest, AsyncChatAcceptedResponse
)
from modules.chat.providers import get_chatbot_service
from modules.chat.services import ChatProcessorService
from modules.auth.providers import get_jwt_service, get_user_repository
from modules.auth.api.deps import get_current_user_id
# Coins integration
from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.services.mission_service import MissionService
from shared.database.connection import get_db, get_db_context
from sqlalchemy.ext.asyncio import AsyncSession
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Security scheme
security = HTTPBearer()





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
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
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
        new_session = ChatSession(id=UUID(session_id), title=data.text[:50], user_id=UUID(user_id))
        await chatbot.chat_repo.create_session(new_session)
    
    # Coins Integration: Deduct 5 coins per message
    coins_repo = SQLAlchemyCoinsRepository(db)
    coins_service = CoinsService(coins_repo)
    
    try:
        await coins_service.spend_coins(
            user_id=UUID(user_id),
            amount=5,
            service_type='ai_chat',
            description=f"AI Chat: {data.text[:30]}"
        )
        
        # Update mission progress: AI Chat count
        mission_repo = SQLAlchemyMissionRepository(db)
        mission_service = MissionService(mission_repo, coins_service)
        await mission_service.update_progress(
            user_id=UUID(user_id),
            mission_type='ai_chat',
            progress_data={'increment': 1, 'field': 'count'}
        )
    except ValueError as e:
        raise HTTPException(status_code=402, detail="Bạn không đủ xu để sử dụng tính năng này. Hãy làm nhiệm vụ để nhận thêm xu!")

    # Use ChatbotService
    try:
        from modules.chat.domain.entities import Message, MessageRole
        # Save user message synchronously before generating
        user_msg_id = str(uuid4())
        await chatbot.chat_repo.add_message(Message(
            id=UUID(user_msg_id),
            session_id=session_id,
            role=MessageRole.USER,
            content=data.text,
            attachments=data.attachments or []
        ))
        
        response_dict = await chatbot.respond(UUID(session_id), data.text, data.attachments, user_msg_id=user_msg_id)
        logger.info(f"✅ Processed message for session: {session_id}")
    except Exception as e:
        logger.error(f"❌ ChatbotService error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return ChatMessageResponse(
        session_id=session_id,
        user_message=data.text,
        bot_response=response_dict["text"],
        created_at=datetime.now()
    )


# ============================================================
# ASYNC ENDPOINTS (Returns 202 with request_id)
# ============================================================

@router.post(
    "/message-async",
    response_model=AsyncChatAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gửi tin nhắn cho AI (Async)",
    description="Gửi tin nhắn và nhận request_id. Kết quả sẽ được gửi qua WebSocket."
)
async def send_message_async(
    data: AsyncChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Gửi tin nhắn cho AI một cách async.
    
    Returns 202 Accepted với request_id, task_id.
    Kết quả sẽ được gửi qua Redis Pub/Sub channel: chat:session:{session_id}:ready
    
    Frontend nên subscribe tới WebSocket endpoint để nhận cập nhật:
    - ws://localhost:8000/ws/chat/{session_id}
    """
    from datetime import datetime
    
    try:
        # Create session if needed
        session_id = data.session_id or str(uuid4())
        
        if not data.session_id:
            from modules.chat.domain.entities import ChatSession
            from modules.chat.providers import get_chat_repository
            chat_repo = get_chat_repository()
            new_session = ChatSession(id=UUID(session_id), title=data.text[:50], user_id=UUID(user_id))
            await chat_repo.create_session(new_session)
        
        # Coins Integration: Deduct coins from config per message
        from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository, SQLAlchemyCoinConfigRepository
        from modules.coins.domain.services.coins_service import CoinsService
        from modules.coins.domain.services.mission_service import MissionService
        
        coins_repo = SQLAlchemyCoinsRepository(db)
        coins_service = CoinsService(coins_repo)
        config_repo = SQLAlchemyCoinConfigRepository(db)
        
        try:
            coin_config_chat = await config_repo.get_config('ai_chat')
            cost_chat = coin_config_chat.cost if coin_config_chat else 5
            
            coin_config_tree = await config_repo.get_config('generate_tree')
            cost_tree = coin_config_tree.cost if coin_config_tree else 10
            
            # 1. Total cost check: Check if user has enough for BOTH chat and a potential tree generation.
            # Tree generation cost is checked upfront but NOT deducted here. It will be deducted in celery task if needed.
            current_balance = await coins_service.get_balance(user_id=UUID(user_id))
            if current_balance < (cost_chat + cost_tree):
                raise ValueError(f"Cần ít nhất {cost_chat + cost_tree} xu để vừa chat vừa tạo cây kỹ năng.")
            
            # 2. Only deduct chat cost here 
            await coins_service.spend_coins(
                user_id=UUID(user_id),
                amount=cost_chat,
                service_type='ai_chat',
                description=f"AI Chat: {data.text[:30]}"
            )
            
            # Update mission progress
            mission_repo = SQLAlchemyMissionRepository(db)
            mission_service = MissionService(mission_repo, coins_service)
            await mission_service.update_progress(
                user_id=UUID(user_id),
                mission_type='ai_chat',
                progress_data={'increment': 1, 'field': 'count'}
            )
        except ValueError as e:
            raise HTTPException(status_code=402, detail=f"{str(e)} Hãy làm nhiệm vụ để nhận thêm xu!")
        
        # Process async
        result = await ChatProcessorService.process_chat_message(
            session_id=UUID(session_id),
            user_message=data.text,
            user_id=UUID(user_id),
            attachments=data.attachments
        )
        
        logger.info(f"✅ Chat message queued for async processing: {result['request_id']}")
        
        return AsyncChatAcceptedResponse(
            request_id=result['request_id'],
            session_id=result['session_id'],
            task_id=result['task_id']
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to queue async chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/message-async-stream",
    summary="Gửi tin nhắn và nhận progress qua HTTP streaming",
    description="Server-Sent Events (SSE) - stream progress updates từng giây"
)
async def send_message_async_stream(
    data: AsyncChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    HTTP Streaming endpoint - bắn progress updates qua SSE
    
    Client nhận dòng JSON events:
    - data: {"type":"started","request_id":"...","session_id":"..."}
    - data: {"type":"progress","progress":25,"step":"intent_extraction"}
    - data: {"type":"progress","progress":50,"step":"rag_query"}
    - data: {"type":"completed","tree":{...}}
    - data: {"type":"error","error":"..."}
    
    Frontend usage:
    ```js
    const eventSource = new EventSource('/api/chat/message-async-stream?session_id=xxx');
    eventSource.onmessage = (e) => {
        const event = JSON.parse(e.data);
        // Update progress bar
    };
    ```
    """
    import asyncio
    import time
    from fastapi.responses import StreamingResponse
    
    async def stream_progress():
        """Generator function để stream progress updates"""
        try:
            # Create session if needed
            session_id = data.session_id or str(uuid4())
            
            if not data.session_id:
                from modules.chat.domain.entities import ChatSession
                from modules.chat.providers import get_chat_repository
                chat_repo = get_chat_repository()
                new_session = ChatSession(id=UUID(session_id), title=data.text[:50], user_id=UUID(user_id))
                await chat_repo.create_session(new_session)
            
            # Coins Integration: Deduct coins from config per message
            from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository, SQLAlchemyCoinConfigRepository
            from modules.coins.domain.services.coins_service import CoinsService
            from modules.coins.domain.services.mission_service import MissionService
            
            coins_repo = SQLAlchemyCoinsRepository(db)
            coins_service = CoinsService(coins_repo)
            config_repo = SQLAlchemyCoinConfigRepository(db)
            
            try:
                coin_config_chat = await config_repo.get_config('ai_chat')
                cost_chat = coin_config_chat.cost if coin_config_chat else 5
                
                coin_config_tree = await config_repo.get_config('generate_tree')
                cost_tree = coin_config_tree.cost if coin_config_tree else 10
                
                current_balance = await coins_service.get_balance(user_id=UUID(user_id))
                if current_balance < (cost_chat + cost_tree):
                    raise ValueError(f"Cần ít nhất {cost_chat + cost_tree} xu để vừa chat vừa tạo cây kỹ năng.")
                
                await coins_service.spend_coins(
                    user_id=UUID(user_id),
                    amount=cost_chat,
                    service_type='ai_chat',
                    description=f"AI Chat: {data.text[:30]}"
                )
                
                # Update mission progress
                mission_repo = SQLAlchemyMissionRepository(db)
                mission_service = MissionService(mission_repo, coins_service)
                await mission_service.update_progress(
                    user_id=UUID(user_id),
                    mission_type='ai_chat',
                    progress_data={'increment': 1, 'field': 'count'}
                )
            except ValueError as e:
                yield f"data: {json.dumps({'type': 'error', 'error': 'insufficient_coins', 'message': f'{str(e)} Hãy làm nhiệm vụ để nhận thêm xu.'})}\n\n"
                return
            
            # Queue to Celery
            result = await ChatProcessorService.process_chat_message(
                session_id=UUID(session_id),
                user_message=data.text,
                user_id=UUID(user_id),
                attachments=data.attachments
            )
            
            request_id = result['request_id']
            task_id = result['task_id']
            
            # Send started event
            yield f"data: {json.dumps({'type': 'started', 'request_id': request_id, 'session_id': session_id, 'task_id': task_id})}\n\n"
            logger.info(f"✅ Stream started for session: {session_id}, request: {request_id}")
            
            # Poll progress from cache every 0.5 seconds
            max_wait = 120  # 2 minutes timeout
            start_time = time.time()
            last_progress = 0
            completed = False
            sent_bot_message = False
            
            from services.redis.event_manager import redis_event_manager
            
            # 🔥 Send the AI response immediately if it already exists in Redis
            try:
                cached_bot_msg = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                if cached_bot_msg:
                    bot_data = json.loads(cached_bot_msg)
                    yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data['text'], 'id': bot_data['id']})}\n\n"
                    logger.info(f"✅ [Stream] Sent initial bot_message from cache for session: {session_id}")
                    sent_bot_message = True
            except Exception as e:
                logger.warning(f"⚠️ [Stream] Failed to fetch initial bot_message from cache: {e}")
            
            while not completed and (time.time() - start_time) < max_wait:
                try:
                    # Poll for bot message if not sent yet
                    if not sent_bot_message:
                        try:
                            cached_bot_msg = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                            if cached_bot_msg:
                                bot_data = json.loads(cached_bot_msg)
                                yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data['text'], 'id': bot_data['id']})}\n\n"
                                logger.info(f"✅ [Stream] Sent polled bot_message from cache for session: {session_id}")
                                sent_bot_message = True
                        except Exception:
                            pass
                            
                    # Get progress from Redis cache
                    cache_key = f"chat:session:{session_id}:current_progress"
                    cache_value = await redis_event_manager.get_cache(cache_key)
                    
                    progress_data = {}
                    if cache_value:
                        try:
                            progress_data = json.loads(cache_value)
                        except:
                            pass
                            
                    # If cache is missing, check DB status
                    from modules.chat.providers import get_chat_repository
                    chat_repo = get_chat_repository()
                    if not cache_value and chat_repo:
                        session_db = await chat_repo.get_session(UUID(session_id))
                        if session_db and session_db.status == "idle":
                            # Make sure to send bot message before completing
                            if not sent_bot_message:
                                cached_bot_msg_retry = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                                if cached_bot_msg_retry:
                                    try:
                                        bot_data_retry = json.loads(cached_bot_msg_retry)
                                        yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data_retry['text'], 'id': bot_data_retry['id']})}\n\n"
                                        sent_bot_message = True
                                    except Exception:
                                        pass
                                
                                # If still not sent, fetch from DB
                                if not sent_bot_message:
                                    try:
                                        db_messages = await chat_repo.get_session_messages(UUID(session_id), limit=1)
                                        if db_messages and len(db_messages) > 0 and db_messages[0].role.value == 'assistant':
                                            bot_msg = db_messages[0]
                                            yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_msg.content, 'id': str(bot_msg.id)})}\n\n"
                                            sent_bot_message = True
                                            logger.info(f"✅ [Stream] Recovered bot_message from DB for session: {session_id}")
                                    except Exception as db_err:
                                        logger.warning(f"⚠️ [Stream] Could not recover bot_message from DB: {db_err}")
                            
                            yield f"data: {json.dumps({'type': 'completed', 'progress': 100, 'tree': session_db.context_data.get('tree_nodes') if session_db.context_data else None})}\n\n"
                            logger.info(f"✅ [Stream] Completed (recovered from DB) for session: {session_id}")
                            completed = True
                            break
                    
                    current_progress = progress_data.get("progress", 0)
                    current_status = progress_data.get("status", "rendering")
                    step = progress_data.get("step", "")
                    
                    # Send progress if changed or first time
                    if current_progress != last_progress or (last_progress == 0 and current_progress > 0):
                        yield f"data: {json.dumps({'type': 'progress', 'progress': current_progress, 'step': step, 'status': current_status})}\n\n"
                        logger.debug(f"📊 Stream progress: {current_progress}% - {step}")
                        last_progress = current_progress
                    
                    # Check if completed
                    if current_status == "idle" and current_progress == 100:
                        if not sent_bot_message:
                            try:
                                db_messages = await chat_repo.get_session_messages(UUID(session_id), limit=1)
                                if db_messages and len(db_messages) > 0 and db_messages[0].role.value == 'assistant':
                                    bot_msg = db_messages[0]
                                    yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_msg.content, 'id': str(bot_msg.id)})}\n\n"
                                    sent_bot_message = True
                            except Exception:
                                pass
                                
                        tree_data = progress_data.get("tree")
                        yield f"data: {json.dumps({'type': 'completed', 'progress': 100, 'tree': tree_data})}\n\n"
                        logger.info(f"✅ Stream completed for session: {session_id}")
                        completed = True
                        break
                    
                    elif current_status == "error":
                        yield f"data: {json.dumps({'type': 'error', 'error': 'processing_failed', 'message': step})}\n\n"
                        logger.warning(f"⚠️ Stream error for session: {session_id} - {step}")
                        break
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error in stream polling: {e}")
                
                # Wait 0.5 seconds before polling again
                await asyncio.sleep(0.5)
            
            if not completed:
                # Timeout reached
                logger.warning(f"⏱️ Stream timeout for session: {session_id} after {max_wait}s")
                yield f"data: {json.dumps({'type': 'timeout', 'message': f'Timeout after {max_wait}s'})}\n\n"
        
        except Exception as e:
            logger.error(f"❌ Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': 'stream_error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(stream_progress(), media_type="text/event-stream")


@router.get(
    "/session/{session_id}/progress-stream",
    summary="Stream progress của existing task",
    description="HTTP streaming - stream progress updates của task đang chạy"
)
async def stream_session_progress(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Stream progress of existing Celery task.
    Frontend calls this after getting 'tree_task_started' event from WebSocket.
    
    Yields SSE events:
    - data: {"type":"progress","progress":25,"step":"intent_extraction"}
    - data: {"type":"completed","tree":{...}}
    - data: {"type":"error","message":"..."}
    """
    import asyncio
    import time
    from fastapi.responses import StreamingResponse
    
    async def stream_progress():
        try:
            from services.redis.event_manager import redis_event_manager
            from modules.chat.providers import get_chat_repository
            
            chat_repo = None
            try:
                chat_repo = get_chat_repository()
            except Exception as e:
                logger.error(f"❌ [Stream] Failed to get chat repository: {e}")
            
            logger.info(f"📡 [Stream] Starting progress stream for session: {session_id}")
            
            max_wait = 120  # 2 minutes timeout
            start_time = time.time()
            last_progress = 0
            completed = False
            sent_bot_message = False
            
            # 🔥 NEW: Send the AI response immediately if it already exists in Redis
            try:
                cached_bot_msg = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                if cached_bot_msg:
                    bot_data = json.loads(cached_bot_msg)
                    yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data['text'], 'id': bot_data['id']})}\n\n"
                    logger.info(f"✅ [Stream] Sent initial bot_message from cache for session: {session_id}")
                    sent_bot_message = True
            except Exception as e:
                logger.warning(f"⚠️ [Stream] Failed to fetch initial bot_message from cache: {e}")
            
            while not completed and (time.time() - start_time) < max_wait:
                try:
                    # Poll for bot message if not sent yet
                    if not sent_bot_message:
                        try:
                            cached_bot_msg = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                            if cached_bot_msg:
                                bot_data = json.loads(cached_bot_msg)
                                yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data['text'], 'id': bot_data['id']})}\n\n"
                                logger.info(f"✅ [Stream] Sent polled bot_message from cache for session: {session_id}")
                                sent_bot_message = True
                        except Exception as e:
                            pass # suppress polling errors
                            
                    # Get progress from Redis cache
                    cache_key = f"chat:session:{session_id}:current_progress"
                    cache_value = await redis_event_manager.get_cache(cache_key)
                    
                    progress_data = {}
                    if cache_value:
                        try:
                            progress_data = json.loads(cache_value)
                        except:
                            pass
                    
                    # Fix: If cache is missing (expired), check DB status
                    # If DB says idle, we should complete immediately
                    if not cache_value and chat_repo:
                        session_db = await chat_repo.get_session(UUID(session_id))
                        if session_db and session_db.status == "idle":
                            # Make sure to send bot message before completing
                            if not sent_bot_message:
                                cached_bot_msg_retry = await redis_event_manager.get_cache(f"chat:session:{session_id}:bot_message")
                                if cached_bot_msg_retry:
                                    try:
                                        bot_data_retry = json.loads(cached_bot_msg_retry)
                                        yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_data_retry['text'], 'id': bot_data_retry['id']})}\n\n"
                                        sent_bot_message = True
                                    except Exception:
                                        pass
                                
                                # If still not sent, fetch from DB
                                if not sent_bot_message:
                                    try:
                                        db_messages = await chat_repo.get_session_messages(UUID(session_id), limit=1)
                                        if db_messages and len(db_messages) > 0 and db_messages[0].role.value == 'assistant':
                                            bot_msg = db_messages[0]
                                            yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_msg.content, 'id': str(bot_msg.id)})}\n\n"
                                            sent_bot_message = True
                                            logger.info(f"✅ [Stream] Recovered bot_message from DB for session: {session_id}")
                                    except Exception as db_err:
                                        logger.warning(f"⚠️ [Stream] Could not recover bot_message from DB: {db_err}")
                            
                            # DB says done, but cache is gone -> Completed
                            yield f"data: {json.dumps({'type': 'completed', 'progress': 100, 'tree': session_db.context_data.get('tree_nodes') if session_db.context_data else None})}\n\n"
                            logger.info(f"✅ [Stream] Completed (recovered from DB) for session: {session_id}")
                            completed = True
                            break

                    current_progress = progress_data.get("progress", 0)
                    current_status = progress_data.get("status", "rendering")
                    step = progress_data.get("step", "")
                    
                    # Send progress if changed
                    if current_progress != last_progress or (last_progress == 0 and current_progress > 0):
                        yield f"data: {json.dumps({'type': 'progress', 'progress': current_progress, 'step': step, 'status': current_status})}\n\n"
                        logger.debug(f"📊 [Stream] Progress: {current_progress}% - {step}")
                        last_progress = current_progress
                    
                    # Check if completed
                    if current_status == "idle" and current_progress == 100:
                        if not sent_bot_message:
                            try:
                                db_messages = await chat_repo.get_session_messages(UUID(session_id), limit=1)
                                if db_messages and len(db_messages) > 0 and db_messages[0].role.value == 'assistant':
                                    bot_msg = db_messages[0]
                                    yield f"data: {json.dumps({'type': 'bot_message', 'text': bot_msg.content, 'id': str(bot_msg.id)})}\n\n"
                                    sent_bot_message = True
                            except Exception:
                                pass
                                
                        tree_data = progress_data.get("tree")
                        yield f"data: {json.dumps({'type': 'completed', 'progress': 100, 'tree': tree_data})}\n\n"
                        logger.info(f"✅ [Stream] Completed for session: {session_id}")
                        completed = True
                        break
                    
                    elif current_status == "error":
                        error_msg = step or "Processing failed"
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                        logger.warning(f"⚠️ [Stream] Error for session: {session_id} - {error_msg}")
                        break
                    
                except Exception as e:
                    logger.warning(f"⚠️ [Stream] Error polling progress: {e}")
                
                # Wait 0.5 seconds before polling again
                await asyncio.sleep(0.5)
            
            if not completed:
                logger.warning(f"⏱️ [Stream] Timeout for session {session_id} after {max_wait}s")
                yield f"data: {json.dumps({'type': 'timeout', 'message': f'Timeout after {max_wait}s'})}\n\n"
        
        except Exception as e:
            logger.error(f"❌ [Stream] Error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(stream_progress(), media_type="text/event-stream")


@router.get(
    "/session/{session_id}/status",
    summary="Get chat session status and progress",
    description="Check if task is still processing or completed. Returns current progress and tree if done."
)
async def get_session_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get session status and task progress
    
    Returns:
    {
        "session_id": str,
        "status": "idle|rendering|error",
        "request_id": str,
        "progress": int (0-100),
        "tree": {...} (if completed),
        "error": str (if error)
    }
    """
    try:
        from modules.chat.infrastructure.models import ChatSessionModel
        from modules.chat.infrastructure.repository import ChatRepositoryImpl
        from sqlalchemy import select
        import json
        
        session_uuid = UUID(session_id)
        repo = ChatRepositoryImpl()
        
        # Get session from DB
        session = await repo.get_session(session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get progress from Redis cache
        from services.redis.event_manager import redis_event_manager
        cache_key = f"chat:session:{session_id}:current_progress"
        cache_value = await redis_event_manager.get_cache(cache_key)
        
        progress_data = {}
        if cache_value:
            try:
                progress_data = json.loads(cache_value)
            except:
                progress_data = {}
        
        # Determine accurate status
        has_active_progress = bool(progress_data) and progress_data.get("progress", 0) < 100
        if has_active_progress:
            status = "rendering"
        else:
            status = session.status if session.status == "rendering" else "idle"

        # Build response
        response = {
            "session_id": session_id,
            "status": status,
            "request_id": str(session.request_id) if session.request_id else None,
            "progress": progress_data.get("progress", 0) if has_active_progress else 100,
            "step": progress_data.get("step", ""),
            "tree": None,
            "error": None
        }
        
        # Add tree if completed
        if session.status == "idle" and session.context_data:
            response["tree"] = session.context_data.get("tree")
            response["progress"] = 100
        
        # Add error if failed
        if session.status == "error":
            response["error"] = progress_data.get("step", "Processing failed")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="Lấy danh sách chat sessions"
)
async def list_sessions(limit: int = 5, offset: int = 0, user_id: UUID = Depends(get_current_user_id)):
    """Lấy danh sách chat sessions với pagination (load more)"""
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    sessions = await repo.get_recent_sessions(limit=limit, offset=offset, user_id=user_id)
    
    return [
        ChatSessionResponse(
            id=str(s.id),
            title=s.title,
            context_data=s.context_data,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list,
    summary="Lấy tin nhắn của session"
)
async def get_session_messages(session_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Lấy tất cả tin nhắn của một session"""
    from uuid import UUID
    from modules.chat.api.schemas import MessageResponse
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    messages = await repo.get_session_messages(UUID(session_id))
    
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role.value,
            content=m.content,
            attachments=m.attachments, # Added attachments
            created_at=m.created_at
        )
        for m in messages
    ]


@router.get(
    "/session/{session_id}",
    summary="Load full chat session",
    description="Get complete session state including messages and context data on page enter"
)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Load complete chat session on page enter.
    Used when navigating to /chat/c/{session_id}
    
    Returns:
    {
        "session_id": str,
        "title": str,
        "status": "idle|rendering|error",
        "progress": int (0-100),
        "messages": [{role, content, created_at}],
        "context_data": {...},
        "created_at": datetime,
        "updated_at": datetime
    }
    """
    try:
        from modules.chat.infrastructure.repository import ChatRepositoryImpl
        
        repo = ChatRepositoryImpl()
        session_uuid = UUID(session_id)
        
        # Get session from DB
        session = await repo.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = await repo.get_session_messages(session_uuid)
        
        # Get progress from Redis
        from services.redis.event_manager import redis_event_manager
        cache_key = f"chat:session:{session_id}:current_progress"
        cache_value = await redis_event_manager.get_cache(cache_key)
        
        progress_data = {}
        if cache_value:
            try:
                progress_data = json.loads(cache_value)
            except:
                progress_data = {}
        
        # Determine status based on progress data
        has_active_progress = bool(progress_data) and progress_data.get("progress", 0) < 100
        
        # If no active progress but DB says rendering, respect DB status
        # This fixes the issue when frontend polls before Celery updates Redis
        if has_active_progress:
            status = "rendering"
        else:
            status = session.status if session.status == "rendering" else "idle"
        
        # Build response
        # Extract only tree_nodes from context_data for FE
        context_response = None
        if session.context_data and "tree_nodes" in session.context_data:
            context_response = {
                "tree_nodes": session.context_data["tree_nodes"]
            }
        
        return {
            "session_id": session_id,
            "title": session.title,
            "status": status,
            "progress": progress_data.get("progress", 0) if has_active_progress else 100,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role.value,
                    "content": m.content,
                    "attachments": m.attachments,
                    "created_at": m.created_at
                }
                for m in messages
            ],
            "context_data": context_response,  # Only tree_nodes, not full context
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to load session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/session/{session_id}/progress",
    summary="Get chat session progress (for polling)",
    description="Lightweight endpoint for polling task progress during rendering"
)
async def get_session_progress(
    session_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get current progress for polling.
    Frontend calls this every 1-2 seconds while session.status == 'rendering'
    
    Returns:
    {
        "session_id": str,
        "status": "idle|rendering|error",
        "progress": int (0-100),
        "step": str (human-readable step name),
        "request_id": str
    }
    """
    try:
        from modules.chat.infrastructure.repository import ChatRepositoryImpl
        
        repo = ChatRepositoryImpl()
        session_uuid = UUID(session_id)
        
        # Get session from DB
        session = await repo.get_session(session_uuid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get progress from Redis cache
        from services.redis.event_manager import redis_event_manager
        cache_key = f"chat:session:{session_id}:current_progress"
        cache_value = await redis_event_manager.get_cache(cache_key)
        
        progress_data = {}
        if cache_value:
            try:
                progress_data = json.loads(cache_value)
            except:
                progress_data = {}
        
        # Build response
        return {
            "session_id": session_id,
            "status": session.status or "idle",
            "progress": progress_data.get("progress", 0) if session.status == "rendering" else (100 if session.status == "idle" else 0),
            "step": progress_data.get("step", ""),
            "request_id": str(session.request_id) if session.request_id else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get session progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/sessions/{session_id}",
    summary="Xóa chat session"
)
async def delete_session(session_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Xóa session và tất cả tin nhắn của nó"""
    from uuid import UUID
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    
    repo = ChatRepositoryImpl()
    deleted = await repo.delete_session(UUID(session_id))
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """
    Unified WebSocket endpoint for:
    - Bidirectional chat (send/receive messages)
    - Async updates from Celery worker (progress, tree ready, errors)
    - User authentication (via token)
    - Session management
    - Skill Tree generation and persistence
    """
    logger.info("🔌 [WS] New connection attempt")
    await websocket.accept()
    logger.info("✅ [WS] Connection accepted")
    
    # Get Chat Repository
    chat_repo = None
    try:
        from modules.chat.providers import get_chat_repository
        chat_repo = get_chat_repository()
    except Exception as e:
        logger.error(f"❌ [WS] Failed to get chat repo: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": "service_error",
                "message": f"Failed to initialize chat service: {str(e)}"
            }))
        except:
            pass
        await websocket.close(code=1011, reason="Service error")
        return

    # Message handler loop
    try:
        while True:
            raw_msg = await websocket.receive_text()
            logger.info(f"📨 [WS] Received: {raw_msg[:100]}")
            
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
            
            # Handle ping
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                logger.info("📤 [WS] Sent pong")
                continue
            
            # Handle user message - queue to Celery
            if msg_type == "user_message":
                try:
                    text = (data.get("text") or "").strip()
                    session_id = data.get("session_id")
                    token = data.get("token")
                    attachments = data.get("attachments", [])
                    
                    if not text:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "empty_text",
                            "message": "Text cannot be empty"
                        }))
                        continue
                    
                    # Extract user_id from token
                    user_id = None
                    if token:
                        try:
                            logger.info(f"🔍 [WS] Processing token: type={type(token)}, len={len(token)}")
                            # logger.info(f"🔍 [WS] Token content: {token[:20]}...") 
                            
                            jwt_service = get_jwt_service()
                            uid_str = jwt_service.get_user_id_from_token(token)
                            
                            if uid_str:
                                user_id = UUID(uid_str)
                                logger.info(f"🔑 [WS] User authenticated: {user_id}")
                        except Exception as e:
                            logger.exception(f"⚠️ [WS] Token processing failed: {e}")
                    
                    # If no session_id, create session IMMEDIATELY
                    if not session_id:
                        session_id = str(uuid4())
                        from modules.chat.domain.entities import ChatSession
                        new_session = ChatSession(
                            id=UUID(session_id),
                            title=text[:50],
                            user_id=user_id
                        )
                        await chat_repo.create_session(new_session)
                        logger.info(f"✅ [WS] Session created: {session_id}")
                    
                    # Coins Integration: Deduct coins before queuing
                    skip_bot_response = False
                    if user_id:
                        from shared.database.connection import get_db_context
                        async with get_db_context() as db:
                            try:
                                from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository, SQLAlchemyCoinConfigRepository
                                from modules.coins.domain.services.coins_service import CoinsService
                                from modules.coins.domain.services.mission_service import MissionService
                                
                                coins_repo = SQLAlchemyCoinsRepository(db)
                                coins_service = CoinsService(coins_repo)
                                config_repo = SQLAlchemyCoinConfigRepository(db)
                                
                                coin_config_chat = await config_repo.get_config('ai_chat')
                                cost_chat = coin_config_chat.cost if coin_config_chat else 5
                                
                                coin_config_tree = await config_repo.get_config('generate_tree')
                                cost_tree = coin_config_tree.cost if coin_config_tree else 10
                                
                                current_balance = await coins_service.get_balance(user_id=user_id)
                                if current_balance < (cost_chat + cost_tree):
                                    raise ValueError(f"Cần ít nhất {cost_chat + cost_tree} xu để vừa chat vừa tạo cây kỹ năng.")
                                
                                await coins_service.spend_coins(
                                    user_id=user_id,
                                    amount=cost_chat,
                                    service_type='ai_chat',
                                    description=f"AI Chat (Async WS): {text[:30]}"
                                )
                                
                                mission_repo = SQLAlchemyMissionRepository(db)
                                mission_service = MissionService(mission_repo, coins_service)
                                await mission_service.update_progress(
                                    user_id=user_id,
                                    mission_type='ai_chat',
                                    progress_data={'increment': 1, 'field': 'count'}
                                )
                            except ValueError as e:
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "error": "insufficient_coins",
                                    "message": f"{str(e)} Hãy làm nhiệm vụ để nhận thêm xu!",
                                    "session_id": session_id
                                }))
                                logger.info(f"🚫 [WS] User {user_id} insufficient coins: {e}")
                                continue
                            except Exception as e:
                                logger.error(f"❌ [WS] Deduct coins error: {e}")
                    
                    # Save request_id + status to chat_sessions BEFORE queuing Celery
                    request_id = str(uuid4())
                    await chat_repo.update_session_status(
                        UUID(session_id),
                        status='rendering',
                        request_id=request_id
                    )
                    logger.info(f"✅ [WS] Session status set to rendering: {request_id}")
                    
                    # Queue to Celery
                    logger.info(f"🎯 [WS] Queuing chat message: session={session_id}, request={request_id}")
                    result = await ChatProcessorService.process_chat_message(
                        session_id=UUID(session_id),
                        user_message=text,
                        user_id=user_id,
                        attachments=attachments
                    )
                    
                    # Send back session_id + user message for immediate UI rendering + streaming
                    await websocket.send_text(json.dumps({
                        "type": "tree_task_started",
                        "request_id": request_id,
                        "session_id": session_id,
                        "task_id": result['task_id'],
                        "user_message": {
                            "id": result.get('user_message_id'),
                            "text": text,
                            "role": "user",
                            "attachments": [{"id": a.get("id"), "filename": a.get("filename")} for a in attachments] if attachments else []
                        },
                        "attachments": [{"id": a.get("id"), "filename": a.get("filename")} for a in attachments] if attachments else [],
                        "message": f"Processing... request_id: {request_id}"
                    }))
                    
                    logger.info(f"📤 [WS] Sent task_started: {request_id}")
                    
                except Exception as e:
                    logger.error(f"❌ [WS] Failed to queue message: {e}", exc_info=True)
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "processing_error",
                        "message": f"Failed to process message: {str(e)}"
                    }))
                continue
            
            # Unknown message type
            logger.warning(f"⚠️ [WS] Unknown message type: {msg_type}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": "unknown_type",
                "message": f"Unknown message type: {msg_type}"
            }))

    
    except Exception as e:
        logger.error(f"❌ [WS] Error: {e}", exc_info=True)
    finally:
        logger.info("🔌 [WS] Connection closed")

    
    
    # Track active session for Redis subscription
    active_session_id = None
    redis_task = None
    
    try:
        while True:
            try:
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
                    session_id = str(uuid4())
                    active_session_id = session_id
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
                    
                    from modules.chat.domain.entities import ChatSession
                    
                    # 1. User Identification
                    token = data.get("token")
                    user_id = None
                    if token:
                        try:

                            jwt_service = get_jwt_service()
                            uid_str = jwt_service.get_user_id_from_token(token)
                            if uid_str:
                                user_id = UUID(uid_str)
                        except Exception as e:
                            logger.warning(f"⚠️ [WS] Invalid token: {e}")

                    # 2. Session Management
                    if not session_id:
                        session_id = str(uuid4())
                        new_session = ChatSession(
                            id=UUID(session_id), 
                            title=text[:50],
                            user_id=user_id
                        )
                        await chat_repo.create_session(new_session)
                        
                        await websocket.send_text(json.dumps({
                            "type": "session_started",
                            "session_id": session_id
                        }))
                    else:
                        existing_session = await chat_repo.get_session(UUID(session_id))
                        if not existing_session:
                            new_session = ChatSession(
                                id=UUID(session_id), 
                                title=text[:50],
                                user_id=user_id
                            )
                            await chat_repo.create_session(new_session)
                            logger.info(f"✨ [WS] Created missing session: {session_id}")
                    
                    # Update active session
                    active_session_id = session_id
                    
                    # 3. Status Update
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": "thinking",
                        "session_id": session_id
                    }))
                    
                    try:
                        # 4. Chat Processing
                        attachments = data.get("attachments", [])
                        
                        # 4.1 Coins & Missions Integration
                        skip_bot_response = False
                        if user_id:
                            from shared.database.connection import get_db_context
                            async with get_db_context() as db:
                                try:
                                    # Coins Integration: Deduct coins from config per message
                                    from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository, SQLAlchemyCoinConfigRepository
                                    from modules.coins.domain.services.coins_service import CoinsService
                                    from modules.coins.domain.services.mission_service import MissionService
                                    
                                    coins_repo = SQLAlchemyCoinsRepository(db)
                                    coins_service = CoinsService(coins_repo)
                                    config_repo = SQLAlchemyCoinConfigRepository(db)
                                    
                                    coin_config_chat = await config_repo.get_config('ai_chat')
                                    cost_chat = coin_config_chat.cost if coin_config_chat else 5
                                    
                                    coin_config_tree = await config_repo.get_config('generate_tree')
                                    cost_tree = coin_config_tree.cost if coin_config_tree else 10
                                    
                                    current_balance = await coins_service.get_balance(user_id=user_id)
                                    if current_balance < (cost_chat + cost_tree):
                                        raise ValueError(f"Cần ít nhất {cost_chat + cost_tree} xu để vừa chat vừa tạo cây kỹ năng.")
                                    
                                    await coins_service.spend_coins(
                                        user_id=user_id,
                                        amount=cost_chat,
                                        service_type='ai_chat',
                                        description=f"AI Chat (WS): {text[:30]}"
                                    )
                                    
                                    # Update mission progress: AI Chat count
                                    mission_repo = SQLAlchemyMissionRepository(db)
                                    mission_service = MissionService(mission_repo, coins_service)
                                    await mission_service.update_progress(
                                        user_id=user_id,
                                        mission_type='ai_chat',
                                        progress_data={'increment': 1, 'field': 'count'}
                                    )
                                except ValueError as e:
                                    await websocket.send_text(json.dumps({
                                        "type": "error",
                                        "error": "insufficient_coins",
                                        "message": f"{str(e)} Hãy làm nhiệm vụ để nhận thêm xu!",
                                        "session_id": session_id
                                    }))
                                    skip_bot_response = True
                                    continue
                                except Exception as e:
                                    logger.error(f"❌ [WS] Deduct coins/mission error: {e}")

                        if not skip_bot_response:
                            # 5. Route to Celery Worker
                            logger.info(f"🎯 [WS] Delegating to Celery Worker...")
                            
                            try:
                                result = await ChatProcessorService.process_chat_message(
                                    session_id=UUID(session_id),
                                    user_message=text,
                                    user_id=user_id,
                                    attachments=attachments
                                )
                                request_id = result['request_id']
                                logger.info(f"📊 [WS] Worker task queued: {request_id}")
                                
                                # Tell frontend we are processing
                                await websocket.send_text(json.dumps({
                                    "type": "status",
                                    "status": "thinking",
                                    "session_id": session_id
                                }))
                                
                                # 🔥 NEW: Subscribe to Redis Pub/Sub for this session
                                # Cancel previous subscription if exists
                                if redis_task and not redis_task.done():
                                    redis_task.cancel()
                                
                                # Convert session_id to int for channel naming
                                session_id_int = int(session_id.replace('-', '')[:8], 16) % (2**31)
                                channels = [
                                    f"chat:session:{session_id_int}:reply",
                                    f"chat:session:{session_id_int}:render",
                                    f"chat:session:{session_id_int}:ready",
                                    f"chat:session:{session_id_int}:error"
                                ]
                                
                                async def forward_redis_events(channel: str, message: dict):
                                    """Forward Redis events to WebSocket"""
                                    try:
                                        await websocket.send_text(json.dumps(message))
                                        logger.debug(f"📤 [WS] Forwarded event from {channel}")
                                    except Exception as e:
                                        logger.warning(f"⚠️ [WS] Failed to forward event: {e}")
                                        raise
                                
                                # Start Redis subscription in background
                                from services.redis.event_manager import redis_event_manager
                                redis_task = asyncio.create_task(
                                    redis_event_manager.subscribe(channels, forward_redis_events)
                                )
                                logger.info(f"🔔 [WS] Subscribed to Redis channels for session {session_id}")
                                
                            except Exception as celery_err:
                                logger.error(f"❌ [WS] Failed to queue task: {celery_err}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "error": "task_failed",
                                    "message": "Lỗi hệ thống.",
                                    "session_id": session_id
                                }))
                    except Exception as processing_err:
                        logger.error(f"❌ [WS] Processing Error: {processing_err}", exc_info=True)
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "error": "processing_failed",
                            "message": str(processing_err),
                            "session_id": session_id
                        }))
                    
                    # 6. Status Update (Idle or Processing)
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "status": "idle",
                        "session_id": session_id
                    }))
                    continue

                # Unknown type
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "unknown_type",
                    "message": f"Unknown message type: {msg_type}"
                }))

            except WebSocketDisconnect:
                logger.info("[WS] Client disconnected in loop")
                break
            except Exception as loop_err:
                logger.error(f"❌ [WS] Loop Error: {loop_err}", exc_info=True)
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "internal_error",
                        "message": "Server internal error"
                    }))
                except Exception:
                    break
                continue
    
    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as fatal_err:
        logger.critical(f"❌ [WS] Fatal Connection Error: {fatal_err}", exc_info=True)
    finally:
        # Cleanup: Cancel Redis subscription task
        if redis_task and not redis_task.done():
            redis_task.cancel()
            logger.info(f"🔕 [WS] Cancelled Redis subscription for session {active_session_id}")


# ============================================================
# ASYNC WEBSOCKET ENDPOINT (For Phase 4 Async Chat)
# ============================================================

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_async(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for async chat with real-time progress updates
    
    Connection flow:
    1. Client connects with session_id
    2. Server sends "welcome_back" with current progress/tree
    3. Server subscribes to Redis Pub/Sub channels
    4. Client receives real-time progress updates
    
    Events received:
    - welcome_back: Current status and progress when connecting
    - rendering_progress: Progress updates (10%, 40%, 70%)
    - tree_ready: Tree completed with full data
    - error: Processing failed
    """
    await websocket.accept()
    
    try:
        from modules.chat.infrastructure.repository import ChatRepositoryImpl
        from services.redis.event_manager import redis_event_manager
        import asyncio
        
        logger.info(f"🔗 [WS-ASYNC] Client connected to session: {session_id}")
        
        repo = ChatRepositoryImpl()
        session_uuid = UUID(session_id)
        
        # Step 1: Get session status
        session = await repo.get_session(session_uuid)
        if not session:
            await websocket.send_json({
                "type": "error",
                "error": "session_not_found",
                "message": f"Session {session_id} not found"
            })
            await websocket.close(code=1008)
            return
        
        # Step 2: Get current progress from cache
        cache_key = f"chat:session:{session_id}:current_progress"
        cache_value = await redis_event_manager.get_cache(cache_key)
        
        progress_data = {}
        if cache_value:
            try:
                progress_data = json.loads(cache_value)
            except:
                progress_data = {}
        
        # Step 3: Send welcome_back event
        welcome_message = {
            "type": "welcome_back",
            "session_id": session_id,
            "status": session.status or "idle",
            "progress": progress_data.get("progress", 0),
            "step": progress_data.get("step", ""),
            "tree": None
        }
        
        # If completed, include tree
        if session.status == "idle" and session.context_data:
            welcome_message["tree"] = session.context_data.get("tree")
            welcome_message["progress"] = 100
        
        await websocket.send_json(welcome_message)
        logger.info(f"📨 [WS-ASYNC] Sent welcome_back event for {session_id}")
        
        # Step 4: Subscribe to Redis Pub/Sub channels for this session
        session_id_int = int(session_id.replace('-', '')[:8], 16) % (2**31)
        channels = [
            f"chat:session:{session_id_int}:render",
            f"chat:session:{session_id_int}:ready",
            f"chat:session:{session_id_int}:error"
        ]
        
        async def on_message(channel: str, message: dict):
            """Handle Pub/Sub messages"""
            try:
                await websocket.send_json(message)
                logger.debug(f"📤 [WS-ASYNC] Sent message from {channel}")
            except Exception as e:
                logger.warning(f"⚠️ [WS-ASYNC] Failed to send message: {e}")
                raise
        
        # Start subscribing in background task
        try:
            await redis_event_manager.subscribe(channels, on_message)
        except Exception as e:
            logger.error(f"❌ [WS-ASYNC] Subscription error: {e}")
            await websocket.close(code=1011)
    
    except Exception as e:
        logger.error(f"❌ [WS-ASYNC] Error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": "internal_error",
                "message": str(e)
            })
        except:
            pass
    
    finally:
        logger.info(f"🔌 [WS-ASYNC] Client disconnected from session: {session_id}")
