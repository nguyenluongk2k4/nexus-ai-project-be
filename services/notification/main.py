import json
import asyncio
import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from shared.security.jwt_service import JWTService

app = FastAPI(title="NexusAI Notification Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.redis_client = None
        self.pubsub = None

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"🔌 [WS] User {user_id} connected. Total users: {len(self.active_connections)}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"🔌 [WS] User {user_id} disconnected.")

    async def send_personal_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            message_json = json.dumps(message)
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message_json)
                except:
                    pass

    async def listen_to_redis(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(settings.NOTIFICATION_CHANNEL)
        
        print(f"📡 [Notification] Listening on Redis channel: {settings.NOTIFICATION_CHANNEL}")
        
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    user_id = data.get("user_id")
                    payload = data.get("payload")
                    if user_id:
                        await self.send_personal_message(user_id, payload)
                    else:
                        # Broadcast
                        for uid in list(self.active_connections.keys()):
                            await self.send_personal_message(uid, payload)
                except Exception as e:
                    print(f"❌ [Notification] Error processing Redis message: {e}")

manager = WebSocketManager()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(manager.listen_to_redis())

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    user_id = None
    if token:
        try:
            jwt_service = JWTService()
            payload = jwt_service.decode_token(token)
            user_id = payload.get("sub")
        except:
            pass

    if not user_id:
        await websocket.close(code=1008)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep alive and wait for client to close
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        print(f"❌ WS error: {e}")
        manager.disconnect(user_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
