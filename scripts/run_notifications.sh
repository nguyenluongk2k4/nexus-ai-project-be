#!/bin/bash

# NexusAI - Notification Service Runner (Dev)
# Chạy Notification Service (WS) với auto-reload

echo "🔔 Starting Notification Service (WebSocket)..."

# Ensure we are in the backend directory
cd "$(dirname "$0")/.."

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run uvicorn
export REDIS_URL=redis://localhost:6379/0
uvicorn services.notification.main:app --reload --port 8002 --host 0.0.0.0
