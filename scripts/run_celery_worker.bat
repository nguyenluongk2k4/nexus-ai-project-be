@echo off
:: NexusAI - Celery Worker Runner (Dev)
:: Chạy Celery Worker xử lý background tasks (chat intent, rendering, etc.)

echo [Target] Starting Celery Worker for Chat Processing...

:: Ensure we are in the backend directory
cd /d "%~dp0.."

:: Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Environment variables
set "PYTHONPATH=%PYTHONPATH%;%cd%"
set "REDIS_URL=redis://localhost:6379/0"
set "CELERY_BROKER_URL=redis://localhost:6379/0"
set "CELERY_RESULT_BACKEND=redis://localhost:6379/1"
set "LOG_LEVEL=info"

:: Check if Redis is running
netstat -an | find "6379" | find "LISTENING" >nul
if errorlevel 1 (
    echo [Warning]  Redis is not running!
    echo [Hint] Start Redis with: .\scripts\run_redis.bat
) else (
    echo [Success] Redis is accessible
)

echo [Info] Starting Celery worker with:
echo    - Module: config.celery_config
echo    - Concurrency: 1 worker
echo    - LogLevel: info
echo.
echo [Hint] Monitor tasks with Flower (start separately):
echo    celery -A config.celery_config flower
echo.

:: Run Celery worker with auto-reload disabled for stability
celery -A config.celery_config worker --loglevel=info --concurrency=1 --queues=default,chat_intent --prefetch-multiplier=4 --task-events
