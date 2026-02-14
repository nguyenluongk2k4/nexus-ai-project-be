#!/bin/bash

# Start Celery Worker using Docker Compose
# Requires: Docker, Docker Compose, .env file configured

set -e

echo "================================================"
echo "Starting Celery Worker"
echo "================================================"
echo ""

# Check if base services are running
echo "Checking base services..."
if ! docker ps | grep -q nexusai-redis-dev; then
    if ! docker ps | grep -q nexusai-redis; then
        echo "❌ Redis not running. Start it first:"
        echo "   ./scripts/run_redis.sh"
        echo "   OR"
        echo "   cd .. && docker-compose up -d redis"
        exit 1
    fi
fi

echo "✅ Base services detected"
echo ""

# Start Celery worker + Flower
echo "Starting Celery worker + Flower..."
docker-compose -f docker-compose.worker.yml up -d

echo ""
echo "✅ Services started!"
echo ""
echo "Celery Worker:"
echo "  Logs: docker logs -f nexusai-celery-worker"
echo "  Stop:  docker-compose -f docker-compose.worker.yml down"
echo ""
echo "Flower (Monitoring):"
echo "  URL: http://localhost:5555"
echo ""
echo "================================================"
