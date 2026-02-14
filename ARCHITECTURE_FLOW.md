# 🎯 Chat System Architecture - Complete Flow Diagram

## 📊 End-to-End System Flow

```plaintext
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMPREHENSIVE FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **Phase 1️⃣: Database Schema (✅ COMPLETED)**

```sql
chat_sessions:
├── id (UUID) → Primary Key
├── user_id (UUID) → Foreign Key
├── title (VARCHAR 255)
├── status (VARCHAR 20) → 'idle' | 'rendering' ✅ NEW
├── request_id (UUID, unique) → Track async request ✅ NEW
├── context_data (JSONB) → Store tree data
├── created_at, updated_at

chat_events: ✅ NEW TABLE
├── id (UUID) → Primary Key
├── chat_session_id (UUID FK)
├── event_type (VARCHAR) → intent_detected | rendering_progress | tree_ready | error
├── payload (JSONB)
├── created_at, updated_at
```

---

### **Phase 2️⃣: Redis & Celery Setup (✅ COMPLETED)**

```
┌─────────────────────────────────────────────────┐
│          Redis Pub/Sub Channels                 │
├─────────────────────────────────────────────────┤
│ chat:session:{id}:intent    (FE → BE)          │
│ chat:session:{id}:render    (Worker → FE)      │
│ chat:session:{id}:ready     (Worker → FE)      │
│ chat:session:{id}:error     (Worker → FE)      │
└─────────────────────────────────────────────────┘

Celery Queue: chat_intent
├── Queue Name: chat_intent
├── Worker Concurrency: 4
├── Broker: Redis (port 6379)
├── Backend: Redis (port 6379/1)
└── Monitoring: Flower (port 5555)

Configuration:
├── CELERY_BROKER_URL: redis://localhost:6379/0
├── CELERY_RESULT_BACKEND: redis://localhost:6379/1
├── TASK_TIMEOUT: 300 seconds
└── AUTO_RETRY: 3 times with exponential backoff
```

---

### **Phase 3️⃣: API Layer (✅ COMPLETED)**

```
REQUEST FLOW:

User (Frontend)
    ↓
POST /chat/message-async
    ↓
ChatProcessorService.process_chat_message()
    │
    ├─ Generate request_id (UUID)
    ├─ Publish intent event to Redis
    ├─ Enqueue process_chat_intent Celery task
    └─ Return 202 Accepted immediately
         {
           "request_id": "uuid",
           "session_id": "uuid",
           "task_id": "celery-task-uuid",
           "status": "processing"
         }
    
Complete (< 100ms) ✅ Non-blocking

WebSocket:
    ↓
Frontend connects: ws://localhost:8000/ws/chat/{session_id}
    ↓
Receives events in real-time (rendering progress, tree_ready, error)
```

---

### **Phase 4️⃣-6️⃣: Background Processing (🔧 IN PROGRESS)**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    process_chat_intent Celery Task                          │
│                          (Synchronous)                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Input Parameters:
├── session_id: str (UUID)
├── user_message: str (user's question)
├── request_id: str (UUID for tracking)
├── user_id: Optional[str]
└── attachments: Optional[List]

═══════════════════════════════════════════════════════════════════════════════

STEP 1️⃣: UPDATE SESSION STATUS
├─ Update DB: chat_sessions.status = 'rendering'
└─ Signal Backend: Session is processing

STEP 2️⃣: PUBLISH RENDERING_STARTED EVENT (10% progress)
├─ Event Channel: chat:session:{id}:render
├─ Event Type: rendering_progress
├─ Payload:
│  {
│    "session_id": 123,
│    "status": "rendering",
│    "progress": 10,
│    "type": "rendering_progress"
│  }
└─ Frontend: Show loading bar (10%)

═══════════════════════════════════════════════════════════════════════════════

STEP 3️⃣: EXTRACT INTENT FROM USER MESSAGE (Gemini)
├─ Component: GeminiIntentService (NEW - Phase 4)
├─ Input: user_message
├─ Process:
│  ├─ Build prompt for intent extraction
│  ├─ Call Gemini API (gemini-2.5-flash)
│  └─ Parse intent (learning_path, find_job, etc.)
├─ Output: intent, extracted_keywords
└─ Example:
      User: "Tôi muốn học Python"
      Intent: "learning_path"
      Keywords: ["Python", "programming"]

═══════════════════════════════════════════════════════════════════════════════

STEP 4️⃣: QUERY RAG FOR DOCUMENTS (40% progress)
├─ Component: RAGService (NEW - Phase 4)
├─ Input: user_message + intent + keywords
├─ Process:
│  ├─ Publish progress event (40%)
│  ├─ Use ChromaAdapter to search vector DB
│  └─ Retrieve top 3-5 relevant documents
├─ Output: List of relevant learning resources
└─ Example:
      Query: "How to learn Python"
      Results:
      ├─ Python Basics course
      ├─ Python Advanced concepts
      └─ Python best practices

═══════════════════════════════════════════════════════════════════════════════

STEP 5️⃣: RENDER SKILL TREE (70% progress)
├─ Component: TreeRenderService (NEW - Phase 4)
├─ Input: intent + documents + user_id
├─ Process:
│  ├─ Publish progress event (70%)
│  ├─ Load skill tree templates from DB
│  ├─ Filter nodes based on intent & RAG results
│  ├─ Build tree structure with icons/colors
│  ├─ Assign difficulty levels
│  └─ Add learning resources to tree
├─ Output: Tree JSON structure
└─ Example:
      {
        "id": "root",
        "name": "Python Learning Path",
        "nodes": [
          {
            "id": "1",
            "label": "Python Basics",
            "level": 1,
            "icon": "📚",
            "status": "not_started",
            "resources": [...]
          },
          ...
        ]
      }

═══════════════════════════════════════════════════════════════════════════════

STEP 6️⃣: STORE TREE DATA & UPDATE SESSION
├─ Save tree to: chat_sessions.context_data
├─ Also create: chat_event record (event_type = 'tree_ready')
└─ Store metadata: processing_time, model_used, etc.

═══════════════════════════════════════════════════════════════════════════════

STEP 7️⃣: PUBLISH TREE_READY EVENT (100% progress)
├─ Event Channel: chat:session:{id}:ready
├─ Event Type: tree_ready
├─ Payload:
│  {
│    "session_id": 123,
│    "status": "idle",
│    "tree": {...entire tree object...},
│    "type": "tree_ready"
│  }
└─ Frontend: Stop loading, display tree ✅

═══════════════════════════════════════════════════════════════════════════════

STEP 8️⃣: RESET SESSION STATUS
├─ Update DB: chat_sessions.status = 'idle'
└─ Signal Frontend: Session ready for next input

═══════════════════════════════════════════════════════════════════════════════

✅ TASK SUCCESS
Return:
{
  "request_id": "uuid",
  "session_id": "uuid",
  "status": "completed",
  "tree": {...}
}

❌ ON ERROR (Any Step)
├─ Catch exception
├─ Log error details
├─ Publish error event
│  {
│    "session_id": 123,
│    "error": "Error message",
│    "error_type": "processing_error",
│    "status": "idle",
│    "type": "error"
│  }
├─ Reset status to 'idle'
├─ Retry (max 3 times)
└─ Return: { "status": "failed", "error": "..." }
```

---

## 🔄 Real-Time Event Flow (Frontend)

```
User opens chat → WebSocket connect
                      ↓
        ws://localhost:8000/ws/chat/{session_id}
                      ↓
        Subscribe to Redis channels:
        ├─ chat:session:{id}:render
        ├─ chat:session:{id}:ready
        └─ chat:session:{id}:error
                      ↓
        User sends message → POST /message-async (202)
                      ↓
        Frontend receives request_id
                      ↓
        Wait for WebSocket events:
        
        Event 1: rendering_progress (10%)
        ├─ Show loading indicator
        └─ Update progress bar
        
        Event 2: rendering_progress (40%)
        ├─ Show "Querying documents..."
        └─ Update progress bar
        
        Event 3: rendering_progress (70%)
        ├─ Show "Rendering tree..."
        └─ Update progress bar
        
        Event 4: tree_ready (100%)
        ├─ Hide loading
        ├─ Display skill tree on UI
        ├─ Enable interactions
        └─ User can navigate tree ✅
```

---

## 🗂️ Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER MAP                                   │
└─────────────────────────────────────────────────────────────────────────────┘

API Layer:
├── POST /chat/message-async
│   └─ ChatProcessorService.process_chat_message()
│       ├─ Generate request_id
│       ├─ Publish intent event
│       └─ Enqueue Celery task

Background Worker (Celery):
├── process_chat_intent (Sync task)
│   ├─ GeminiIntentService.extract_intent()      [Phase 4 NEW]
│   │   └─ Call Gemini API
│   ├─ RAGService.query_documents()               [Phase 4 NEW]
│   │   └─ Call ChromaAdapter
│   └─ TreeRenderService.render_tree()            [Phase 4 NEW]
│       └─ Build tree from nodes + resources

Redis Event Manager:
├── Publish intent event
├── Publish rendering progress
├── Publish tree_ready event
└─ Publish error event on failure

Database Layer:
├── ChatSession (update status, store tree)
├── Chat event (audit log)
└─ Learning resources, skill nodes (read)
```

---

## 📋 Phase 4 Implementation Roadmap

### **Phase 4.1: GeminiIntentService (NEW)**
```
File: backend/modules/chat/services/gemini_intent_service.py

Class: GeminiIntentService
├── __init__(llm_adapter: GeminiAdapter)
├── extract_intent(user_message: str) → {intent, keywords, confidence}
├── _build_intent_prompt(message: str) → str
└── _parse_intent_response(response: str) → dict

Intents Supported:
├─ learning_path: "Tôi muốn học X"
├─ find_job: "Các công việc liên quan đến X"
├─ practice: "Bài tập về X"
├─ resource: "Nguồn học về X"
└─ general: Default

Example:
  Input: "Tôi muốn học Python từ cơ bản"
  Output: {
    "intent": "learning_path",
    "keywords": ["Python", "basics"],
    "confidence": 0.95
  }
```

### **Phase 4.2: RAGService (NEW)**
```
File: backend/modules/chat/services/rag_service.py

Class: RAGService
├── __init__(vector_store: ChromaAdapter)
├── query_documents(query: str, n_results: int = 5) → List[str]
├── query_with_filters(query: str, filters: dict) → List[dict]
└── rank_results(results: List, query: str) → List[dict]

Example:
  Input: "Python programming basics"
  Output: [
    {
      "id": "doc1",
      "content": "Python is a...",
      "score": 0.92,
      "source": "documentation"
    },
    ...
  ]
```

### **Phase 4.3: TreeRenderService (NEW)**
```
File: backend/modules/chat/services/tree_renderer_service.py

Class: TreeRenderService
├── __init__(skill_tree_repo: SkillTreeRepository)
├── render_tree(intent: str, documents: List, user_id: UUID) → dict
├── _build_tree_structure(nodes: List, documents: List) → dict
├── _assign_levels(nodes: List) → List
└── _attach_resources(nodes: List, documents: List) → List

Example:
  Input: intent="learning_path", docs=[...], user_id=...
  Output: {
    "id": "root",
    "name": "Python Learning Path",
    "nodes": [{...}, ...],
    "metadata": {
      "intent": "learning_path",
      "documents_used": 5,
      "generated_at": "..."
    }
  }
```

---

## 🔌 Dependencies & Integration

```
Existing Components Used:
├── GeminiAdapter (/shared/llm/gemini_adapter.py)
│   ├─ Method: generate(prompt: str) → str
│   └─ Used for: Intent extraction + prompting
├── ChromaAdapter (/shared/vector_store/chroma_adapter.py)
│   ├─ Method: search(query: str, n_results: int) → List[str]
│   └─ Used for: RAG document retrieval
├── ChatbotService (existing, sync)
│   ├─ Used for: Reference architecture
│   └─ New: Extract reusable logic
└── SkillTreeService (existing)
    ├─ Used for: Loading tree templates
    └─ New: Tree generation based on intent

New Components Created:
├── GeminiIntentService [Phase 4]
├── RAGService [Phase 4]
├── TreeRenderService [Phase 4]
└── process_chat_intent Celery task
```

---

## 📊 Data Flow Diagram

```
┌────────────┐
│  Frontend  │
└─────┬──────┘
      │ POST /message-async
      ▼
┌─────────────────────────────┐
│   ChatProcessorService      │  ← Generates request_id
│   (API Layer - Fast)        │  ← Publishes intent event
│   Returns 202 in < 100ms    │  ← Enqueues task
└──────────┬──────────────────┘
           │
     Redis → Celery Queue
           │
           ▼
┌─────────────────────────────┐
│ Celery Worker Task          │  ← Sync process_chat_intent
│ (Background - Async flow)   │
└──────┬──────────────┬───────┘
       │              │
       ├─ Step 3◄────┤ GeminiIntentService
       │  Intent     │ (extract intent)
       │  ▼
       │ Step 4◄─────┤ RAGService
       │  Documents  │ (query ChromaDB)
       │  ▼
       │ Step 5◄─────┤ TreeRenderService
       │  Tree       │ (render tree)
       │
   Redis Events (progress)
       │
       ▼
   Frontend WebSocket
       │
       ├─ rendering_progress (10%, 40%, 70%)
       └─ tree_ready (100%) → Display tree ✅
```

---

## 🚀 Execution Timeline

```
T=0ms       : User sends message via POST /message-async
T=50ms      : Receive 202 Accepted + request_id
             (Request enqueued in Celery)

T=100ms     : Celery worker picks up task
T=150ms     : Publishing progress event (10%)
T=500ms     : Gemini intent extraction done
T=550ms     : Publishing progress event (40%)
T=1500ms    : RAG query complete + retrieve docs
T=1550ms    : Publishing progress event (70%)
T=2500ms    : Tree rendering complete
T=2550ms    : Publishing tree_ready event (100%)
T=2600ms    : Frontend receives tree ✅

Total: ~2.5 seconds end-to-end
```

---

## 🔒 Error Handling Flow

```
Any Exception at Any Step:
├─ Catch in try/except
├─ Log error with context
├─ Publish error event to Redis
│  {
│    "type": "error",
│    "error": "descriptive error message",
│    "error_type": "intent_extraction_error|rag_error|render_error|etc"
│  }
├─ Update session.status = 'idle'
├─ Celery auto-retry (max 3 times, exponential backoff)
└─ If max retries exceeded:
   └─ Store error in chat_events table
   └─ Frontend shows error: "Processing failed, try again"
```

---

## ✅ Success Criteria for Phase 4-6

**Phase 4 Complete When:**
- [ ] GeminiIntentService extracts intents correctly
- [ ] RAGService retrieves relevant documents
- [ ] TreeRenderService generates valid tree JSON
- [ ] All services integrate into process_chat_intent task
- [ ] Redis events published at each stage
- [ ] Error handling works end-to-end

**Phase 5 Complete When:**
- [ ] Database updates (session status) work
- [ ] Tree data persisted in context_data
- [ ] Chat events logged to DB
- [ ] Full task lifecycle tested

**Phase 6 Complete When:**
- [ ] Frontend WebSocket receives events
- [ ] UI displays progress updates
- [ ] Tree renders on client side
- [ ] End-to-end test passes

---

## 📝 File Summary

```
CREATED/MODIFIED:
├── backend/config/
│   ├── settings.py (✅ Redis + Celery config)
│   └── celery_config.py (✅ Celery app setup)
├── backend/services/
│   ├── redis/event_manager.py (✅ Pub/Sub manager)
│   └── task_processor/
│       ├── celery_app (in __init__.py) (✅)
│       └── chat_intent_worker.py (will become tasks.py)
├── backend/modules/chat/
│   ├── tasks.py (✅ process_chat_intent task - WIP)
│   ├── services/__init__.py (✅ ChatProcessorService)
│   ├── services/gemini_intent_service.py (🔧 Phase 4)
│   ├── services/rag_service.py (🔧 Phase 4)
│   ├── services/tree_renderer_service.py (🔧 Phase 4)
│   ├── infrastructure/models.py (✅ status + request_id)
│   └── api/schemas.py (✅ Async schemas)
├── backend/migrations/
│   ├── 001_add_session_chat_status.sql (✅)
│   ├── 002_create_chat_events_table.sql (✅)
│   └── 003_add_request_id.sql (✅)
└── backend/docker-compose.worker.yml (✅ Fixed)
```

---

**Ready for Phase 4 Implementation!** 🚀
