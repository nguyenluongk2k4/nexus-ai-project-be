#!/bin/bash

# NexusAI - Infrastructure Runner (Dev)
# Chạy Redis broker bằng Docker

echo "🚀 Starting Redis for local development..."
docker run --name nexusai-redis-dev -d -p 6379:6379 redis:7-alpine 2>/dev/null || docker start nexusai-redis-dev

echo "✅ Redis is running on localhost:6379"
echo "💡 Use 'docker stop nexusai-redis-dev' to stop."
