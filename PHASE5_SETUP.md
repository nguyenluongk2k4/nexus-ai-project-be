# NexusAI Backend - Phase 5 & 6 Setup

## Quick Start

### 1. Install & Setup Backend

```bash
cd backend/
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This will:
- ✅ Create Python virtual environment
- ✅ Install dependencies from requirements.txt + pytest
- ✅ Create .env file (add your API keys)
- ✅ Prepare database

### 2. Start Services (Docker)

```bash
# Start base services (PostgreSQL, Redis, ChromaDB)
docker-compose up -d db redis chromadb

# Wait for services to be healthy (~10 seconds)
docker-compose logs db | grep "ready to accept"
```

### 3. Run Database Migrations

```bash
# Create/update tables with required columns
python scripts/run_chat_migrations.py
```

### 4. Run Tests

#### Backend Tests (Phase 5)
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_gemini_intent_service.py -v
pytest tests/test_rag_service.py -v
pytest tests/test_tree_renderer_service.py -v
pytest tests/test_celery_e2e.py -v

# Run with coverage
pytest tests/ --cov=modules.chat --cov-report=html
```

#### Test Files
- **test_gemini_intent_service.py** - 12 tests for intent extraction
- **test_rag_service.py** - 10 tests for document retrieval
- **test_tree_renderer_service.py** - 12 tests for tree generation
- **test_celery_e2e.py** - 9 integration tests for async processing

### 5. Start Celery Worker

#### Option A: Local Development
```bash
# Terminal 1: Celery Worker
celery -A modules.chat.tasks worker --loglevel=info

# Terminal 2: Backend Server (new terminal)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option B: Docker (Production-like)
```bash
# Start Celery worker + Flower monitoring
chmod +x scripts/start_celery_worker.sh
./scripts/start_celery_worker.sh
```

View Flower dashboard: http://localhost:5555

## File Structure

```
backend/
├── requirements.txt                    # Full dependencies
├── requirements.celery_worker.txt      # Minimal for Celery container
├── requirements.notification.txt       # For notification service
│
├── Dockerfile                          # Main backend service
├── Dockerfile.celery_worker           # Celery worker container
├── docker-compose.yml                  # Base services
├── docker-compose.worker.yml          # Celery + Flower
│
├── scripts/
│   ├── setup.sh                        # Initial setup
│   ├── start_celery_worker.sh         # Start Celery (Docker)
│   ├── run_chat_migrations.py         # Database migrations
│   └── ...
│
├── modules/chat/
│   ├── services/
│   │   ├── gemini_intent_service.py   # Intent extraction (Phase 4)
│   │   ├── rag_service.py             # Document retrieval (Phase 4)
│   │   └── tree_renderer_service.py   # Tree generation (Phase 4)
│   │
│   ├── tasks.py                        # Celery task (Phase 4)
│   ├── api/routes.py                   # API endpoints (Phase 4)
│   └── infrastructure/models.py        # Database models
│
├── tests/                              # Phase 5 - Testing
│   ├── test_gemini_intent_service.py
│   ├── test_rag_service.py
│   ├── test_tree_renderer_service.py
│   ├── test_celery_e2e.py
│   └── conftest.py
│
└── ...
```

## Phase 5 - Backend Testing

### Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| GeminiIntentService | 12 | ✅ Ready |
| RAGService | 10 | ✅ Ready |
| TreeRenderService | 12 | ✅ Ready |
| Celery E2E | 9 | ✅ Ready |

### Running Tests

```bash
# All tests
pytest tests/ -v

# Watch mode (auto-rerun on changes)
pytest-watch tests/

# Specific test
pytest tests/test_celery_e2e.py::TestProcessChatIntentTask::test_task_complete_flow_learning_path -v

# With output
pytest tests/ -v -s
```

## Phase 6 - Frontend Integration

The Chat.tsx component has been updated to support async tree rendering:

```typescript
// Features:
- Async task polling (500ms intervals)
- Real-time progress bar (0-100%)
- Skill tree visualization
- Node difficulty colors (beginner/intermediate/advanced)
- Error handling
```

### Frontend Test the Integration

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Send message in chat
4. Observe:
   - Progress bar updates
   - Tree renders when complete
   - Can click nodes for details

## Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis
docker-compose up -d redis
```

### Database Connection Error
```bash
# Check PostgreSQL status
docker-compose logs db

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

### Celery Task Not Processing
```bash
# 1. Check Celery worker logs
docker logs -f nexusai-celery-worker

# 2. Check Flower dashboard
http://localhost:5555

# 3. Verify Redis broker connection
redis-cli ping
```

### Tests Failing
```bash
# 1. Check if services are running
docker-compose ps

# 2. Check .env configuration
cat .env

# 3. Run with verbose output
pytest tests/ -v -s
```

## Environment Variables Required

Create `.env` from template:
```bash
cp env.example .env
```

Add to `.env`:
```env
# Database
DATABASE_URL=postgresql+asyncpg://nexusai:nexusai_password@localhost:5432/nexusai

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_API_KEY=your_google_api_key_here

# App
DEBUG=True
```

## Next Steps

1. ✅ Phase 5: Run pytest tests to validate backend
2. ✅ Phase 6: Test Chat.tsx with backend API
3. 🔄 Phase 7: Load testing & performance optimization
4. 🔄 Phase 8: Production deployment

## Useful Commands

```bash
# View Celery task queue
celery -A modules.chat.tasks inspect active

# View registered tasks
celery -A modules.chat.tasks inspect registered

# Purge all pending tasks
celery -A modules.chat.tasks purge

# Monitor in real-time
celery -A modules.chat.tasks events

# View task history
celery -A modules.chat.tasks inspect reserved
```
