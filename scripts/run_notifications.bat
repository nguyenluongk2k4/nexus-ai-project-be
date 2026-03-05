@echo off
:: NexusAI - Notification Service Runner (Dev)
:: Chạy Notification Service (WS) với auto-reload

echo [Info] Starting Notification Service (WebSocket)...

:: Ensure we are in the backend directory
cd /d "%~dp0.."

:: Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: Run uvicorn
set "REDIS_URL=redis://localhost:6379/0"
uvicorn services.notification.main:app --reload --port 8002 --host 0.0.0.0
