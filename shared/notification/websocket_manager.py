import json
import redis.asyncio as redis
from typing import Any
from config.settings import settings

class RedisNotificationPublisher:
    """Publisher that sends events to Redis for the standalone Socket Server"""
    
    def __init__(self):
        self.redis_client = None
        self.channel = settings.NOTIFICATION_CHANNEL

    async def _get_client(self):
        if self.redis_client is None:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def send_personal_message(self, user_id: str, message: Any):
        """Publish a message for a specific user to Redis"""
        client = await self._get_client()
        data = {
            "user_id": user_id,
            "payload": message
        }
        await client.publish(self.channel, json.dumps(data))
        print(f"📡 [Redis] Published notification for user {user_id}")

    async def broadcast(self, message: Any):
        """Publish a broadcast message to Redis"""
        client = await self._get_client()
        data = {
            "user_id": None,
            "payload": message
        }
        await client.publish(self.channel, json.dumps(data))
        print(f"📡 [Redis] Published broadcast notification")

# Compatibility singleton
notification_manager = RedisNotificationPublisher()
