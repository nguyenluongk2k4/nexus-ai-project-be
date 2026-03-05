@echo off
:: NexusAI - Infrastructure Runner (Dev)
:: Chạy Redis broker bằng Docker

echo [Info] Starting Redis for local development...
docker run --name nexusai-redis-dev -d -p 6379:6379 redis:7-alpine 2>nul || docker start nexusai-redis-dev

echo [Success] Redis is running on localhost:6379
echo [Hint] Use 'docker stop nexusai-redis-dev' to stop.
