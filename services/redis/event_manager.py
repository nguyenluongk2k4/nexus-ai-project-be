# Redis Event Manager
# Handles pub/sub for real-time chat events

import json
import logging
from typing import Optional, Callable, Any, Dict
from datetime import datetime
import redis.asyncio as redis
from config.settings import settings

logger = logging.getLogger(__name__)


class RedisEventManager:
    """
    Manages Redis Pub/Sub for chat session events
    Channels:
    - chat:session:{session_id}:intent         (FE → BE: user input)
    - chat:session:{session_id}:render         (Task → FE: rendering progress)
    - chat:session:{session_id}:ready          (BE → FE: tree ready)
    - chat:session:{session_id}:error          (BE → FE: error)
    """
    
    _instance: Optional["RedisEventManager"] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Connected to Redis for event pub/sub")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.aclose()
            logger.info("🔌 Disconnected from Redis")
    
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active"""
        if self._redis is None:
            await self.connect()
    
    async def publish(self, channel: str, event: Dict[str, Any]) -> int:
        """
        Publish event to Redis channel
        
        Args:
            channel: Redis channel name (e.g., "chat:session:123:ready")
            event: Event data (dict, will be JSON serialized)
        
        Returns:
            Number of subscribers that received the message
        """
        await self._ensure_connected()
        try:
            payload = json.dumps({
                **event,
                "timestamp": datetime.utcnow().isoformat(),
            })
            result = await self._redis.publish(channel, payload)
            logger.debug(f"📤 Event published to {channel}: {result} subscriber(s)")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to publish event to {channel}: {e}")
            raise
    
    async def subscribe(
        self,
        channels: list[str],
        callback: Callable[[str, str], Any]
    ) -> None:
        """
        Subscribe to Redis channels
        
        Args:
            channels: List of channel names
            callback: Async function to handle messages (channel, message)
        """
        await self._ensure_connected()
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(*channels)
            logger.info(f"✅ Subscribed to channels: {channels}")
            
            # Listen for messages
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    await callback(channel, data)
        
        except Exception as e:
            logger.error(f"❌ Subscription error: {e}")
            raise
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()
    
    async def get_channel_pattern(self, session_id: int, event_type: str) -> str:
        """
        Generate channel name for session event
        
        Args:
            session_id: Chat session ID
            event_type: Event type (intent, render, ready, error)
        
        Returns:
            Channel name
        """
        return f"chat:session:{session_id}:{event_type}"
    
    async def publish_intent_event(
        self,
        session_id: int,
        user_message: str,
        request_id: str
    ) -> int:
        """Publish user intent event"""
        channel = await self.get_channel_pattern(session_id, "intent")
        event = {
            "session_id": session_id,
            "user_message": user_message,
            "request_id": request_id,
            "type": "intent_detected"
        }
        return await self.publish(channel, event)
    
    async def publish_rendering_event(
        self,
        session_id: int,
        progress: int,
        status: str = "rendering",
        step: str = ""
    ) -> int:
        """Publish rendering progress event"""
        channel = await self.get_channel_pattern(session_id, "render")
        event = {
            "session_id": session_id,
            "status": status,
            "progress": progress,
            "step": step,
            "type": "rendering_progress"
        }
        return await self.publish(channel, event)
    
    async def publish_ready_event(
        self,
        session_id: int,
        tree_data: Dict[str, Any]
    ) -> int:
        """Publish tree ready event"""
        channel = await self.get_channel_pattern(session_id, "ready")
        
        # Format tree for FE: rename tree_nodes to nodes and remove extra fields
        formatted_tree = None
        if tree_data is not None:
            formatted_tree = {
                "nodes": tree_data.get("tree_nodes", [])
            }
        
        event = {
            "session_id": session_id,
            "status": "idle",
            "tree": formatted_tree,  # FE expects tree.nodes
            "type": "tree_ready"
        }
        return await self.publish(channel, event)
    
    async def publish_error_event(
        self,
        session_id: int,
        error_message: str,
        error_type: str = "processing_error"
    ) -> int:
        """Publish error event"""
        channel = await self.get_channel_pattern(session_id, "error")
        event = {
            "session_id": session_id,
            "error": error_message,
            "error_type": error_type,
            "status": "idle",
            "type": "error"
        }
        return await self.publish(channel, event)
    
    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            await self._ensure_connected()
            pong = await self._redis.ping()
            return pong == "PONG" or pong == True
        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return False
    
    async def set_cache(self, key: str, value: str, ttl: int = 1800) -> bool:
        """
        Set cache value with TTL in Redis
        
        Args:
            key: Cache key
            value: Cache value (JSON string)
            ttl: Time to live in seconds (default: 30 minutes)
        
        Returns:
            True if successful
        """
        try:
            await self._ensure_connected()
            await self._redis.setex(key, ttl, value)
            logger.debug(f"💾 Cached {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache {key}: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[str]:
        """
        Get cache value from Redis
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        try:
            await self._ensure_connected()
            value = await self._redis.get(key)
            if value:
                logger.debug(f"📖 Retrieved cache {key}")
            return value
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve cache {key}: {e}")
            return None
    
    async def _set_cache(self, key: str, value: str, ttl: int = 1800) -> bool:
        """Alias for set_cache (async version)"""
        return await self.set_cache(key, value, ttl)


# Singleton instance
redis_event_manager = RedisEventManager()
