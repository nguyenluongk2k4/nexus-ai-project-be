#!/bin/bash

# Start All NexusAI Backend Services
# Opens 3 terminal windows for Redis, Notifications, and Celery Worker

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting all NexusAI backend services..."
echo "📂 Backend directory: $BACKEND_DIR"

# Check if gnome-terminal is available
if command -v gnome-terminal &> /dev/null; then
    echo "✅ Using gnome-terminal (opening 3 separate windows)"
    
    # Launch each service in a separate terminal window
    gnome-terminal --title="Redis Server" -- bash -c "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_redis.sh; exec bash" &
    sleep 0.5
    
    gnome-terminal --title="Notifications" -- bash -c "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_notifications.sh; exec bash" &
    sleep 0.5
    
    gnome-terminal --title="Celery Worker" -- bash -c "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_celery_worker.sh; exec bash" &
    
    echo "✅ All services started in 3 separate windows!"
    
elif command -v tmux &> /dev/null; then
    echo "✅ Using tmux"
    
    # Create new tmux session
    SESSION_NAME="nexus-backend"
    
    # Kill existing session if exists
    tmux kill-session -t $SESSION_NAME 2>/dev/null
    
    # Start new session with Redis
    tmux new-session -d -s $SESSION_NAME -n "Redis" "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_redis.sh"
    
    # Create new windows for Notifications and Celery
    tmux new-window -t $SESSION_NAME -n "Notifications" "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_notifications.sh"
    tmux new-window -t $SESSION_NAME -n "Celery" "cd '$BACKEND_DIR' && source .venv/bin/activate && bash scripts/run_celery_worker.sh"
    
    # Attach to session
    tmux attach-session -t $SESSION_NAME
    
    echo "✅ All services started in tmux session: $SESSION_NAME"
    
else
    echo "❌ Neither gnome-terminal nor tmux found!"
    echo "Please install one of them:"
    echo "  - gnome-terminal: sudo apt install gnome-terminal"
    echo "  - tmux: sudo apt install tmux"
    exit 1
fi
