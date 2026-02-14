#!/bin/bash

# Backend Setup Script
# Installs dependencies, runs migrations, starts services

set -e

echo "================================================"
echo "NexusAI Backend Setup"
echo "================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Activate virtual environment
echo -e "${BLUE}[1/6]${NC} Checking Python environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# 2. Install dependencies
echo -e "${BLUE}[2/6]${NC} Installing dependencies..."
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q
pip install pytest pytest-asyncio python-dotenv -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 3. Check .env file
echo -e "${BLUE}[3/6]${NC} Checking .env configuration..."
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp env.example .env
    echo -e "${YELLOW}⚠ Update .env with your API keys!${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# 4. Database migrations
echo -e "${BLUE}[4/6]${NC} Running database migrations..."
if command -v psql &> /dev/null; then
    echo "PostgreSQL found, running migrations..."
    python scripts/run_chat_migrations.py 2>/dev/null || echo "Note: Ensure PostgreSQL is running"
else
    echo -e "${YELLOW}⚠ PostgreSQL not found locally, ensure it's running via Docker${NC}"
fi

# 5. Summary
echo -e "${BLUE}[5/6]${NC} Setup Summary:"
echo "  Database: Update DATABASE_URL in .env"
echo "  Redis: Update REDIS_URL in .env"
echo "  Gemini API: Add GOOGLE_API_KEY to .env"

# 6. Ready
echo -e "${BLUE}[6/6]${NC} Setup complete!"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Setup Docker services:"
echo "     cd docker && docker-compose up -d"
echo ""
echo "  2. Run tests:"
echo "     pytest tests/"
echo ""
echo "  3. Start Celery worker:"
echo "     celery -A modules.chat.tasks worker --loglevel=info"
echo ""
echo "  4. Start backend server:"
echo "     uvicorn app.main:app --reload"
echo ""
echo -e "${GREEN}================================================${NC}"
