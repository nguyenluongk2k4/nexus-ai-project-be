#!/bin/bash

# NexusAI - Celery Worker Runner (Dev)
# Chạy Celery Worker xử lý background tasks (chat intent, rendering, etc.)

echo "🎯 Starting Celery Worker for Chat Processing..."

# Ensure we are in the backend directory
cd "$(dirname "$0")/.."

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
export LOG_LEVEL=info

# Check if Redis is running (using Docker or port check)
if ! docker ps | grep -q nexusai-redis; then
    if ! nc -z localhost 6379 2>/dev/null; then
        echo "⚠️  Redis is not running!"
        echo "💡 Start Redis with: ./scripts/run_redis.sh"
        exit 1
    fi
fi

echo "✅ Redis is accessible"
echo "📋 Starting Celery worker with:"
echo "   - Module: config.celery_config"
echo "   - Concurrency: 4 workers"
echo "   - LogLevel: info"
echo ""
echo "💡 Monitor tasks with Flower (start separately):"
echo "   celery -A config.celery_config flower"
echo ""

# Run Celery worker with auto-reload disabled for stability
# Note: Using concurrency=1 to minimize memory usage on VPS (8GB RAM limit)
# Uses CPU instead of CUDA (no GPU available)
celery -A config.celery_config worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=default,chat_intent \
    --prefetch-multiplier=4 \
    --task-events

