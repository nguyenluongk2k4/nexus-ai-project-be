# 🎯 Chat System Refactoring - Status & Phase 4 Roadmap

## 📊 Overall Progress: 50% Complete

```
Phase 1: Database Schema       ✅ COMPLETE (migrations created)
Phase 2: Redis & Celery       ✅ COMPLETE (all config done)
Phase 3: API Layer            ✅ COMPLETE (endpoints set up)
Phase 4: Service Layer        🔧 TO DO (3 new services)
Phase 5: Backend Integration  🔧 TO DO
Phase 6: Frontend Integration 🔧 TO DO
```

---

## ✅ Completed Work

### Phase 1: Database Migrations
```
✅ /migrations/001_add_session_chat_status.sql
   - Adds status column to chat_sessions
   - Default: 'idle'

✅ /migrations/002_create_chat_events_table.sql
   - New table for event audit log
   - Stores: event_type, payload (JSONB), timestamp

✅ /migrations/003_add_request_id.sql
   - Adds unique request_id to track async requests
```

**Status:** Created but NOT YET APPLIED to database
**Next Step:** Run migrations using:
```bash
alembic upgrade head
# or manually via psql
```

---

### Phase 2: Redis & Celery Configuration

#### ✅ Settings Configuration
**File:** [backend/config/settings.py](backend/config/settings.py)
```python
# Redis Config
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHAT_DB = 2  # Separate DB for chat events

# Celery Config
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
CELERY_TASK_SERIALIZER = "json"
```

#### ✅ Celery App Configuration
**File:** [backend/config/celery_config.py](backend/config/celery_config.py)
- Celery task settings
- Queue configuration (chat_intent queue)
- Auto-retry strategy (3x with backoff)
- Result backend setup

#### ✅ Redis Event Manager
**File:** [backend/services/redis/event_manager.py](backend/services/redis/event_manager.py)
- Singleton pattern
- Async Pub/Sub manager
- Event publishing methods:
  - `publish_intent_event(session_id, message, request_id)`
  - `publish_rendering_event(session_id, progress)`
  - `publish_ready_event(session_id, tree_data)`
  - `publish_error_event(session_id, error)`

#### ✅ Docker Compose Configuration
**File:** [backend/docker-compose.worker.yml](backend/docker-compose.worker.yml)
- Celery worker service
- Flower monitoring
- External network reference (nexusai-network)
- Auto-retry configuration

#### ✅ Test Scripts
**Files:**
- [backend/scripts/test_redis_pubsub.py](backend/scripts/test_redis_pubsub.py) - Redis connection test
- [backend/scripts/run_celery_worker.sh](backend/scripts/run_celery_worker.sh) - Local worker launcher

---

### Phase 3: API Layer & Schemas

#### ✅ ChatProcessorService
**File:** [backend/modules/chat/services/__init__.py](backend/modules/chat/services/__init__.py)
```python
class ChatProcessorService:
    async def process_chat_message(
        self,
        session_id: UUID,
        user_message: str,
        user_id: Optional[UUID],
        attachments: Optional[List]
    ) -> dict:
        """
        Returns 202 Accepted immediately with:
        {
          "request_id": UUID,
          "session_id": UUID,
          "task_id": str (Celery task ID),
          "status": "processing"
        }
        """
```

#### ✅ Updated Celery Task Structure
**File:** [backend/modules/chat/tasks.py](backend/modules/chat/tasks.py)
```python
@shared_task(
    name='modules.chat.tasks.process_chat_intent',
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    queue='chat_intent',
    time_limit=300,
)
def process_chat_intent(self, session_id, user_message, request_id, user_id=None, attachments=None):
    # 8-step process with Redis event publishing
    pass
```

#### ✅ API Schemas
**File:** [backend/modules/chat/api/schemas.py](backend/modules/chat/api/schemas.py)
- `AsyncChatRequest`: For POST /message-async
- `AsyncChatAcceptedResponse`: 202 response
- `ChatEventPayload`: Event structure

#### ✅ Updated Models
**File:** [backend/modules/chat/infrastructure/models.py](backend/modules/chat/infrastructure/models.py)
```python
class ChatSessionModel(Base):
    status: str = Column(String(20), default='idle')  # ✅ NEW
    request_id: UUID = Column(UUID, unique=True)      # ✅ NEW
```

---

## 🔧 Phase 4: Service Implementation (TODO)

### 4.1 GeminiIntentService
**File:** `backend/modules/chat/services/gemini_intent_service.py` (NEW)

**Purpose:** Extract user intent from message using Gemini

**Requirements:**
- Use existing GeminiAdapter (reuse, don't rebuild)
- Input: user_message (str)
- Output: intent dict with keys: `intent`, `keywords`, `confidence`

**Implementation Checklist:**
- [ ] Create `GeminiIntentService` class
- [ ] Method: `extract_intent(user_message: str) → dict`
- [ ] Build intent extraction prompt
- [ ] Parse Gemini response
- [ ] Handle API errors gracefully
- [ ] Return normalized intent (learning_path|find_job|practice|resource|general)

**Example:**
```python
service = GeminiIntentService(llm_adapter)
result = service.extract_intent("Tôi muốn học Python từ cơ bản")
# Output: {
#   "intent": "learning_path",
#   "keywords": ["Python", "programming"],
#   "confidence": 0.95
# }
```

**Reference:** Can reuse logic from existing ChatbotService in [backend/modules/chat/domain/services.py](backend/modules/chat/domain/services.py)

---

### 4.2 RAGService
**File:** `backend/modules/chat/services/rag_service.py` (NEW)

**Purpose:** Query RAG system for relevant documents

**Requirements:**
- Use existing ChromaAdapter (reuse, don't rebuild)
- Input: query (str), optional filters
- Output: List of document dicts

**Implementation Checklist:**
- [ ] Create `RAGService` class
- [ ] Method: `query_documents(query: str, n_results: int = 5) → List[dict]`
- [ ] Call ChromaAdapter.search()
- [ ] Format results with metadata
- [ ] Rank by relevance score
- [ ] Handle ChromaDB errors

**Example:**
```python
service = RAGService(vector_store_adapter)
docs = service.query_documents("Python basics", n_results=5)
# Output: [
#   {
#     "id": "doc1",
#     "content": "Python is a…",
#     "score": 0.92,
#     "source": "documentation"
#   },
#   ...
# ]
```

**Reference:** Can reuse logic from existing ChatbotService (modules/chat/domain/services.py)

---

### 4.3 TreeRenderService
**File:** `backend/modules/chat/services/tree_renderer_service.py` (NEW)

**Purpose:** Generate skill tree structure based on intent + RAG results

**Requirements:**
- Load skill tree templates from DB
- Filter nodes based on intent
- Attach resources from RAG results
- Return tree JSON structure

**Implementation Checklist:**
- [ ] Create `TreeRenderService` class
- [ ] Method: `render_tree(intent: str, documents: List, user_id: UUID) → dict`
- [ ] Load skill tree (use existing SkillTreeService or repository)
- [ ] Filter nodes by intent
- [ ] Build tree structure JSON
- [ ] Attach learning resources to nodes
- [ ] Assign difficulty levels

**Example:**
```python
service = TreeRenderService(skill_tree_repo)
tree = service.render_tree(
    intent="learning_path",
    documents=[...],
    user_id=uuid
)
# Output: {
#   "id": "root",
#   "name": "Python Learning Path",
#   "nodes": [
#     {
#       "id": "1",
#       "label": "Basics",
#       "level": 1,
#       "status": "not_started",
#       "resources": [...]
#     }
#   ]
# }
```

**Reference:** Can reference existing [backend/modules/skill_tree/usecases/](backend/modules/skill_tree/usecases/) for tree loading logic

---

## 🔐 Phase 5: Celery Task Implementation (TODO)

**File:** [backend/modules/chat/tasks.py](backend/modules/chat/tasks.py)

**Current State:** Task structure complete, need to fill in TODOs

**8-Step Implementation:**

```python
@shared_task(...)
def process_chat_intent(self, session_id, user_message, request_id, user_id=None, attachments=None):
    """
    Step 1️⃣: Update session status
    """
    # TODO: session.status = 'rendering'

    """
    Step 2️⃣: Publish rendering started event (10%)
    """
    # TODO: call redis_event_manager.publish_rendering_event(session_id, 10)

    """
    Step 3️⃣: Extract intent via Gemini
    """
    # TODO: Call GeminiIntentService.extract_intent(user_message)
    # intent = {...}

    """
    Step 4️⃣: Query RAG for documents (40% progress)
    """
    # TODO: Publish progress event (40%)
    # TODO: Call RAGService.query_documents(user_message)
    # documents = [...]

    """
    Step 5️⃣: Render skill tree (70% progress)
    """
    # TODO: Publish progress event (70%)
    # TODO: Call TreeRenderService.render_tree(intent, documents, user_id)
    # tree = {...}

    """
    Step 6️⃣: Store tree data & create event
    """
    # TODO: session.context_data = tree
    # TODO: Create chat_event record

    """
    Step 7️⃣: Publish tree_ready event (100%)
    """
    # TODO: Call redis_event_manager.publish_ready_event(session_id, tree)

    """
    Step 8️⃣: Reset session status
    """
    # TODO: session.status = 'idle'

    # Error handling: See tasks.py for try/except blocks
```

---

## 🎨 Phase 6: Frontend WebSocket Integration (TODO)

**Requirements:**
- WebSocket endpoint: `ws://localhost:8000/ws/chat/{session_id}`
- Subscribe to Redis events
- Real-time progress updates
- Final tree rendering

**Event Flow:**
```
FE connects to WebSocket
    ↓
Subscribe to channels:
  ├─ chat:session:{id}:render (progress)
  ├─ chat:session:{id}:ready (tree)
  └─ chat:session:{id}:error (error)
    ↓
User sends message → POST /message-async (202)
    ↓
WebSocket receives events:
  ├─ 10% progress
  ├─ 40% progress
  ├─ 70% progress
  ├─ 100% tree_ready
    ↓
Render tree on UI ✅
```

---

## 🚀 Phase 4 Implementation Order

### Recommended Sequence:
1. **GeminiIntentService** (simplest, no external DB)
2. **RAGService** (medium, uses ChromaAdapter)
3. **TreeRenderService** (most complex, DB + tree logic)
4. **Integration in tasks.py** (all pieces together)
5. **Testing & debugging**

---

## 📝 Implementation Template

Each service follows DDD pattern:

```python
# backend/modules/chat/services/SERVICE_NAME.py

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from uuid import UUID
from shared.logger import logger

class ServiceInterface(ABC):
    """Port/Interface definition"""
    @abstractmethod
    def execute(self, ...): pass

class ConcreteService(ServiceInterface):
    """Implementation"""
    def __init__(self, dependencies):
        self.dependencies = dependencies
    
    def execute(self, ...):
        """Implementation with error handling"""
        try:
            # Your logic here
            pass
        except Exception as e:
            logger.error(f"Error in service: {str(e)}", exc_info=True)
            raise

# Usage in tasks.py:
def process_chat_intent(...):
    service = ConcreteService(get_dependencies())
    result = service.execute(...)
```

---

## 🧪 Testing Strategy

### Unit Tests (Phase 4)
```bash
pytest backend/tests/modules/chat/services/test_gemini_intent_service.py
pytest backend/tests/modules/chat/services/test_rag_service.py
pytest backend/tests/modules/chat/services/test_tree_renderer_service.py
```

### Integration Tests (Phase 5)
```bash
pytest backend/tests/modules/chat/test_task_integration.py
```

### End-to-End Tests (Phase 6)
```bash
# Manual WebSocket test
wscat -c ws://localhost:8000/ws/chat/{session_id}

# Or use test script
python backend/scripts/test_e2e_chat.py
```

---

## 📋 Checklist for Phase 4 Completion

### ✅ Definition
- [ ] GeminiIntentService fully documented
- [ ] RAGService fully documented
- [ ] TreeRenderService fully documented
- [ ] All services follow DDD pattern
- [ ] All services have error handling
- [ ] All services use existing adapters (not rebuilding)

### ✅ Implementation
- [ ] `gemini_intent_service.py` created
- [ ] `rag_service.py` created
- [ ] `tree_renderer_service.py` created
- [ ] All services integrated into `tasks.py`
- [ ] Imports and dependencies resolved
- [ ] No syntax errors

### ✅ Testing
- [ ] Unit tests pass for each service
- [ ] Integration tests pass
- [ ] Manual task testing succeeds
- [ ] Redis events published correctly
- [ ] Database updates work
- [ ] Error handling works

### ✅ Documentation
- [ ] Service docstrings complete
- [ ] Parameter types documented
- [ ] Return types documented
- [ ] Error scenarios documented
- [ ] Example usage provided

---

## 📊 Current File Status

```
READY FOR PHASE 4:
├── ✅ /config/settings.py
├── ✅ /config/celery_config.py
├── ✅ /services/redis/event_manager.py
├── ✅ /modules/chat/tasks.py (structure complete)
├── ✅ /modules/chat/services/__init__.py (ChatProcessorService ready)
├── ✅ /modules/chat/infrastructure/models.py
├── ✅ /modules/chat/api/schemas.py
├── ✅ /docker-compose.worker.yml
└── ✅ /migrations/ (001, 002, 003)

TO CREATE (Phase 4):
├── /modules/chat/services/gemini_intent_service.py (NEW)
├── /modules/chat/services/rag_service.py (NEW)
├── /modules/chat/services/tree_renderer_service.py (NEW)
└── /tests/modules/chat/ (test files)

TO UPDATE:
├── /modules/chat/tasks.py (fill in TODOs)
└── /modules/chat/api/routes.py (implement POST /message-async)
```

---

## 🎯 Next Action

**👉 Start Phase 4 Service Implementation**

1. Create [GeminiIntentService](backend/modules/chat/services/gemini_intent_service.py)
   - Use existing [GeminiAdapter](backend/shared/llm/gemini_adapter.py)
   - Extract intent from user message
   - Return: {intent, keywords, confidence}

2. Create [RAGService](backend/modules/chat/services/rag_service.py)
   - Use existing [ChromaAdapter](backend/shared/vector_store/chroma_adapter.py)
   - Query documents from vector DB
   - Return: List[{id, content, score, source}]

3. Create [TreeRenderService](backend/modules/chat/services/tree_renderer_service.py)
   - Load skill trees from DB
   - Build tree structure based on intent
   - Attach resources from RAG results
   - Return: {id, name, nodes[], metadata}

4. Integrate into `process_chat_intent` task
   - Fill in all TODOs
   - Test end-to-end flow

Ready! 🚀

