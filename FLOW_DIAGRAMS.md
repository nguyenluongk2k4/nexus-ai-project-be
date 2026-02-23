# Comprehensive Mermaid Diagrams

## 1. User Request to Tree Rendering Flow

```mermaid
sequenceDiagram
    participant User as User (Browser)
    participant FE as Frontend
    participant API as FastAPI Backend
    participant Redis as Redis Pub/Sub
    participant Celery as Celery Worker
    participant Gemini as Gemini API
    participant ChromaDB as ChromaDB (RAG)
    participant DB as PostgreSQL
    participant WebSocket as WebSocket

    User->>FE: Type message & send
    FE->>API: POST /chat/message-async
    Note over API: Generate request_id

    API->>DB: Update session.status='rendering'
    API->>Redis: Publish intent event (10%)
    API->>Celery: Enqueue process_chat_intent task
    API-->>FE: 202 Accepted (< 100ms)
    FE-->>User: Show loading bar

    par Worker Processing
        Celery->>Gemini: Extract intent from message
        Gemini-->>Celery: Return intent + keywords
        Celery->>Redis: Publish progress event (40%)
        
        Celery->>ChromaDB: Query documents
        ChromaDB-->>Celery: Return top 5 results
        Celery->>Redis: Publish progress event (70%)
        
        Celery->>DB: Load skill tree templates
        Celery->>Celery: Render tree (intent + docs)
        DB-->>Celery: Tree structure
    end

    Celery->>DB: Save tree to context_data
    Celery->>DB: Create chat_event record
    Celery->>Redis: Publish tree_ready event
    Celery->>DB: Update session.status='idle'

    Redis-->>WebSocket: Forward events
    WebSocket-->>FE: Event stream
    FE->>User: Update progress bar (40%, 70%, 100%)
    FE->>User: Display skill tree ✅

    Note over Celery: Total: ~2.5 seconds
```

## 2. Phase 4 Service Architecture

```mermaid
graph TB
    subgraph API["API Layer"]
        CP["ChatProcessorService<br/>(Fast - < 100ms)"]
    end

    subgraph TaskQueue["Celery Task Queue"]
        PCI["process_chat_intent<br/>(Sync)"]
    end

    subgraph Services["Phase 4 Services"]
        GIS["GeminiIntentService<br/>(Extract intent)"]
        RAGS["RAGService<br/>(Query docs)"]
        TRS["TreeRenderService<br/>(Render tree)"]
    end

    subgraph External["External Services"]
        Gemini["Gemini API"]
        ChromaDB["ChromaDB<br/>(Vector Store)"]
    end

    subgraph Storage["Data Layer"]
        DB["PostgreSQL<br/>chat_sessions<br/>chat_events"]
        Cache["Redis<br/>Pub/Sub Events"]
    end

    subgraph Frontend["Frontend"]
        WS["WebSocket"]
        UI["UI Components"]
    end

    CP -->|Enqueue| PCI
    CP -->|Publish| Cache

    PCI -->|Call| GIS
    PCI -->|Call| RAGS
    PCI -->|Call| TRS
    PCI -->|Update| DB
    PCI -->|Publish| Cache

    GIS -->|API Call| Gemini
    RAGS -->|Search| ChromaDB
    TRS -->|Load| DB

    Cache -->|Subscribe| WS
    WS -->|Update| UI
```

## 3. Redis Event Publishing Sequence

```mermaid
graph LR
    A["Celery Task Starts<br/>Status: rendering"] 
    B["Pub: intent (10%)"]
    C["Gemini Extract"]
    D["Pub: progress (40%)"]
    E["RAG Query"]
    F["Pub: progress (70%)"]
    G["Tree Render"]
    H["Pub: ready<br/>Status: idle"]

    A -->|~50ms| B
    B -->|~350ms| C
    C -->|~50ms| D
    D -->|~950ms| E
    E -->|~50ms| F
    F -->|~950ms| G
    G -->|~50ms| H

    style A fill:#ff6b6b
    style B fill:#ffd43b
    style C fill:#74c0fc
    style D fill:#ffd43b
    style E fill:#74c0fc
    style F fill:#ffd43b
    style G fill:#74c0fc
    style H fill:#51cf66
```

## 4. Error Handling Flow

```mermaid
graph TD
    A["process_chat_intent<br/>Running"] -->|Exception| B{Which Step?}
    
    B -->|Intent| C["Catch: intent_extraction_error"]
    B -->|RAG| D["Catch: rag_error"]
    B -->|Tree| E["Catch: render_error"]
    
    C --> F["Log error"]
    D --> F
    E --> F
    
    F --> G["Publish error event"]
    G --> H["Update status='idle'"]
    H --> I["Retry: 3x<br/>exponential backoff"]
    
    I -->|Success| J["✅ Complete"]
    I -->|Fail| K["❌ Max retries<br/>Store in chat_events"]
    
    K --> L["Frontend shows:<br/>Processing failed"]
    
    style A fill:#fff3bf
    style J fill:#51cf66
    style L fill:#ff6b6b
```

## 5. Database State Transitions

```mermaid
stateDiagram-v2
    [*] --> idle: Session created

    idle --> rendering: POST /message-async<br/>Task enqueued

    rendering --> error: Exception at any step
    rendering --> idle: Task completes (tree_ready)

    error --> idle: Error event published<br/>Status reset
    
    idle --> [*]

    note right of rendering
        Status: "rendering"
        Duration: ~2.5s
        Progress events: 10%, 40%, 70%
    end

    note right of error
        Auto-retry: 3x
        Error logged to chat_events
    end
```

## 6. Timing & Performance

```mermaid
timeline
    title Chat Request Processing Timeline (Milliseconds)
    
    section API (Fast)
        0ms : Start POST /message-async
        : Generate request_id
        : Update DB session
        50ms : Publish to Redis
        : Enqueue Celery
        100ms : Return 202 ✅
    
    section Celery (Background)
        100ms : Worker picks up task
        150ms : Publish progress (10%)
        200ms : Gemini API call (starts)
        500ms : Gemini response (intent extracted)
        550ms : Publish progress (40%)
        600ms : ChromaDB query (starts)
        1500ms : ChromaDB response (docs retrieved)
        1550ms : Publish progress (70%)
        1600ms : Tree rendering (starts)
        2500ms : Tree complete
        2550ms : Publish tree_ready (100%) ✅
```

## 7. Service Dependencies

```mermaid
graph TB
    subgraph "Chat Module"
        CP["ChatProcessorService"]
        CT["Celery Task"]
    end

    subgraph "New Services (Phase 4)"
        GIS["GeminiIntentService"]
        RAGS["RAGService"]
        TRS["TreeRenderService"]
    end

    subgraph "Existing Services"
        GA["GeminiAdapter"]
        CA["ChromaAdapter"]
        ST["SkillTreeService"]
    end

    subgraph "Infrastructure"
        Redis["RedisEventManager"]
        DB["ChatRepository"]
    end

    CP -.->|enqueues| CT
    CT -->|calls| GIS
    CT -->|calls| RAGS
    CT -->|calls| TRS
    
    GIS -->|uses| GA
    RAGS -->|uses| CA
    TRS -->|uses| ST
    
    CT -->|publishes via| Redis
    CT -->|updates| DB
    CT -->|loads from| DB
```

---

**All diagrams ready for reference during Phase 4 implementation!**
