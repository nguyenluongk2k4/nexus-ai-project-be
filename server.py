import json
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import existing chatbot logic
from smart_chatbot import SmartChatbot

load_dotenv()

app = FastAPI(title="AI Skill Tree Chat API")

# Allow local dev origins for Vite (3000/5173)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate chatbot once (loads models/DB)
chatbot: Optional[SmartChatbot] = None


@app.on_event("startup")
async def startup_event():
    global chatbot
    chatbot = SmartChatbot()


class NewSessionResponse(BaseModel):
    session_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/session/new", response_model=NewSessionResponse)
async def new_session():
    assert chatbot is not None
    session_id = chatbot.memory.start_new_session()
    return {"session_id": session_id}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    assert chatbot is not None
    await websocket.accept()

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
            except Exception:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "invalid_json",
                    "message": "Message must be valid JSON"
                }))
                continue

            msg_type = data.get("type")
            session_id = data.get("session_id")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "new_session":
                session_id = chatbot.memory.start_new_session()
                await websocket.send_text(json.dumps({
                    "type": "session_started",
                    "session_id": session_id,
                }))
                continue

            if msg_type == "user_message":
                text = (data.get("text") or "").strip()
                if not text:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "empty_text",
                        "message": "Text cannot be empty"
                    }))
                    continue

                # Ensure we have a session
                if not session_id:
                    session_id = chatbot.memory.start_new_session()
                    await websocket.send_text(json.dumps({
                        "type": "session_started",
                        "session_id": session_id,
                    }))

                # Point chatbot memory at this session
                chatbot.memory.current_session_id = session_id

                # Notify client that bot is thinking
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "thinking",
                    "session_id": session_id,
                }))

                # Run inference
                try:
                    answer = chatbot.get_response(text)
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": "inference_failed",
                        "message": str(e),
                        "session_id": session_id,
                    }))
                    continue

                # Send answer
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "text": answer,
                    "session_id": session_id,
                }))
                # Done thinking
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "status": "idle",
                    "session_id": session_id,
                }))
                continue

            # Unknown message type
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": "unknown_type",
                "message": f"Unknown message type: {msg_type}",
            }))

    except WebSocketDisconnect:
        # Client disconnected
        return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
