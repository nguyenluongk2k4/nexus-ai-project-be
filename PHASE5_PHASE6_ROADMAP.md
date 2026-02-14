# 🚀 Phase 5 & Phase 6 Roadmap

## ⏭️ PHASE 5: BACKEND INTEGRATION (Backend Only)

### Objective
Validate and integrate all Phase 4 services, run database migrations, and test the complete backend pipeline.

### Tasks

#### 5.1 Database Migrations 📊
```bash
# Run the 3 migrations created in Phase 1
alembic upgrade head

# Or manually:
psql -h localhost -U nexusai -d nexusai < backend/migrations/001_add_session_chat_status.sql
psql -h localhost -U nexusai -d nexusai < backend/migrations/002_create_chat_events_table.sql
psql -h localhost -U nexusai -d nexusai < backend/migrations/003_add_request_id.sql
```

**Migrations:**
- `001_add_session_chat_status.sql` - Adds `status` + `request_id` columns
- `002_create_chat_events_table.sql` - Creates audit log table
- `003_add_request_id.sql` - Adds unique request_id tracking

#### 5.2 Import & Dependency Validation ✅
```bash
# Test all imports work
python -c "
from modules.chat.services.gemini_intent_service import GeminiIntentService
from modules.chat.services.rag_service import RAGService
from modules.chat.services.tree_renderer_service import TreeRenderService
from modules.chat.tasks import process_chat_intent
print('✅ All imports successful')
"
```

#### 5.3 Services Testing 🧪

**Test 1: GeminiIntentService**
```python
# backend/tests/modules/chat/test_gemini_intent_service.py

import pytest
from modules.chat.services.gemini_intent_service import GeminiIntentService

@pytest.mark.asyncio
async def test_extract_intent_learning():
    service = GeminiIntentService()
    result = await service.extract_intent("Tôi muốn học Python")
    
    assert result["intent"] in ["learning_path", "general"]
    assert len(result["keywords"]) > 0
    assert 0 <= result["confidence"] <= 1

@pytest.mark.asyncio
async def test_extract_intent_job():
    service = GeminiIntentService()
    result = await service.extract_intent("Công việc nào phù hợp cho tôi?")
    
    assert result["intent"] in ["find_job", "general"]
    assert result["confidence"] > 0

@pytest.mark.asyncio
async def test_extract_intent_error_handling():
    service = GeminiIntentService()
    result = await service.extract_intent("")
    
    # Should return default
    assert result["intent"] == "general"
```

**Test 2: RAGService**
```python
# backend/tests/modules/chat/test_rag_service.py

@pytest.mark.asyncio
async def test_query_documents():
    service = RAGService()
    results = await service.query_documents("Python programming", n_results=3)
    
    assert isinstance(results, list)
    if results:
        assert "id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]
        assert 0 <= results[0]["score"] <= 1

@pytest.mark.asyncio
async def test_batch_query_documents():
    service = RAGService()
    results = await service.batch_query_documents(
        ["Python", "JavaScript"],
        n_results=2
    )
    
    assert len(results) == 2
    assert isinstance(results[0], list)
```

**Test 3: TreeRenderService**
```python
# backend/tests/modules/chat/test_tree_renderer_service.py

@pytest.mark.asyncio
async def test_render_tree():
    service = TreeRenderService()
    tree = await service.render_tree(
        intent="learning_path",
        documents=[],
        user_id=None
    )
    
    assert tree["id"] == "root"
    assert "name" in tree
    assert "nodes" in tree
    assert isinstance(tree["nodes"], list)

@pytest.mark.asyncio
async def test_render_tree_with_documents():
    service = TreeRenderService()
    docs = [
        {"content": "Python basics", "score": 0.9},
        {"content": "Advanced Python", "score": 0.85}
    ]
    
    tree = await service.render_tree(
        intent="learning_path",
        documents=docs
    )
    
    assert len(tree["nodes"]) > 0
```

#### 5.4 Celery Task Testing ⚙️

**Test: Full Task Execution**
```python
# backend/tests/modules/chat/test_celery_task.py

import pytest
from modules.chat.tasks import process_chat_intent
from uuid import uuid4

@pytest.mark.asyncio
async def test_process_chat_intent_full_flow():
    session_id = str(uuid4())
    request_id = str(uuid4())
    user_message = "Tôi muốn học Python"
    
    # Call task (will use asyncio.run internally)
    result = process_chat_intent(
        session_id=session_id,
        user_message=user_message,
        request_id=request_id,
        user_id=None
    )
    
    assert result["status"] in ["completed", "failed"]
    assert result["request_id"] == request_id
    if result["status"] == "completed":
        assert "tree" in result
        assert result["tree"]["id"] == "root"

@pytest.mark.asyncio
async def test_process_chat_intent_error_handling():
    session_id = str(uuid4())
    request_id = str(uuid4())
    
    # Test with invalid inputs
    result = process_chat_intent(
        session_id=session_id,
        user_message="",  # Empty
        request_id=request_id
    )
    
    # Should still return result (not crash)
    assert "status" in result
    assert result["request_id"] == request_id
```

#### 5.5 Redis Cache Testing 💾

**Test: Progress Caching**
```python
# backend/tests/services/test_redis_cache.py

@pytest.mark.asyncio
async def test_cache_progress():
    from services.redis.event_manager import redis_event_manager
    import json
    
    key = "chat:session:test123:current_progress"
    value = json.dumps({
        "progress": 40,
        "status": "rendering",
        "step": "rag_query"
    })
    
    # Set cache
    result = await redis_event_manager.set_cache(key, value, ttl=1800)
    assert result == True
    
    # Get cache
    cached = await redis_event_manager.get_cache(key)
    assert cached is not None
    data = json.loads(cached)
    assert data["progress"] == 40

@pytest.mark.asyncio
async def test_cache_expiry():
    from services.redis.event_manager import redis_event_manager
    import asyncio
    
    key = "chat:session:expire_test:progress"
    
    # Set with short TTL
    await redis_event_manager.set_cache(key, "test_value", ttl=1)
    
    # Should exist
    value1 = await redis_event_manager.get_cache(key)
    assert value1 is not None
    
    # Wait for expiry
    await asyncio.sleep(2)
    
    # Should be gone
    value2 = await redis_event_manager.get_cache(key)
    assert value2 is None
```

#### 5.6 Database Status Updates 📝

**Test: Session Status Update**
```python
# backend/tests/modules/chat/test_database_updates.py

@pytest.mark.asyncio
async def test_update_session_status():
    from modules.chat.tasks import _update_session_status
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    from uuid import uuid4
    
    session_id = uuid4()
    repo = ChatRepositoryImpl()
    
    # Create session
    from modules.chat.domain.entities import ChatSession
    session = ChatSession(id=session_id, title="Test")
    await repo.create_session(session)
    
    # Update status
    result = await _update_session_status(session_id, "rendering")
    assert result == True
    
    # Verify
    updated = await repo.get_session(session_id)
    assert updated.status == "rendering"
    
    # Update to idle
    result = await _update_session_status(session_id, "idle")
    assert result == True
    
    updated = await repo.get_session(session_id)
    assert updated.status == "idle"

@pytest.mark.asyncio
async def test_save_tree_to_context():
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    from modules.chat.domain.entities import ChatSession
    from uuid import uuid4
    
    session_id = uuid4()
    repo = ChatRepositoryImpl()
    
    # Create session
    session = ChatSession(id=session_id, title="Test")
    await repo.create_session(session)
    
    # Save tree
    tree_data = {
        "tree": {"id": "root", "name": "Test", "nodes": []},
        "intent": "learning_path"
    }
    result = await repo.update_session_context(session_id, tree_data)
    assert result == True
    
    # Verify
    updated = await repo.get_session(session_id)
    assert updated.context_data["tree"]["name"] == "Test"
```

#### 5.7 End-to-End Backend Test 🎯

**Test: Complete Pipeline**
```bash
# backend/tests/e2e/test_chat_pipeline_e2e.py

@pytest.mark.asyncio
async def test_complete_chat_pipeline():
    """
    E2E test:
    1. Create session
    2. Enqueue task
    3. Wait for completion
    4. Verify tree in DB
    5. Check Redis cache
    """
    from modules.chat.services import ChatProcessorService
    from modules.chat.infrastructure.repository import ChatRepositoryImpl
    from modules.chat.tasks import process_chat_intent
    from services.redis.event_manager import redis_event_manager
    from uuid import uuid4
    import time
    import json
    
    # Setup
    session_id = uuid4()
    repo = ChatRepositoryImpl()
    
    # Create session
    from modules.chat.domain.entities import ChatSession
    session = ChatSession(id=session_id, title="E2E Test")
    await repo.create_session(session)
    
    # Process message
    result = await ChatProcessorService.process_chat_message(
        session_id=session_id,
        user_message="Tôi muốn học Python",
        user_id=None
    )
    
    assert "request_id" in result
    
    # Simulate task execution
    task_result = process_chat_intent(
        session_id=str(session_id),
        user_message="Tôi muốn học Python",
        request_id=result["request_id"]
    )
    
    assert task_result["status"] in ["completed", "failed"]
    
    # Verify DB update
    updated_session = await repo.get_session(session_id)
    assert updated_session.status == "idle"
    assert updated_session.context_data is not None
    
    # Verify Redis cache
    cache_key = f"chat:session:{str(session_id)}:current_progress"
    cache = await redis_event_manager.get_cache(cache_key)
    if cache:
        data = json.loads(cache)
        assert data["progress"] == 100
        assert data["status"] == "idle"
```

#### 5.8 Run Tests
```bash
# Install pytest
pip install pytest pytest-asyncio

# Run all tests
pytest backend/tests/ -v

# Run specific test module
pytest backend/tests/modules/chat/test_gemini_intent_service.py -v

# Run with coverage
pytest backend/tests/ --cov=modules.chat --cov-report=html
```

---

## 📱 PHASE 6: FRONTEND INTEGRATION (React/TypeScript)

### Objective
Update React UI to handle async chat with real-time progress, status checks, and tree display.

### Components to Update

#### 6.1 Chat Page Component 💬
**File:** `frontend/src/modules/chat/pages/ChatPage.tsx`

```typescript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export const ChatPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [status, setStatus] = useState<'idle' | 'rendering' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [tree, setTree] = useState(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Step 1: Check session status on mount
  useEffect(() => {
    checkSessionStatus();
  }, [sessionId]);

  // Step 2: Call GET endpoint to check progress
  const checkSessionStatus = async () => {
    try {
      const response = await fetch(
        `/api/chat/session/${sessionId}/status`
      );
      const data = await response.json();

      setStatus(data.status);
      setProgress(data.progress);

      if (data.status === 'rendering') {
        // Still processing
        setIsLoading(true);
        connectWebSocket();
      } else if (data.status === 'idle' && data.tree) {
        // Already completed
        setIsLoading(false);
        setProgress(100);
        setTree(data.tree);
      } else if (data.status === 'error') {
        setError(data.error);
      }
    } catch (err) {
      console.error('Failed to get status:', err);
    }
  };

  // Step 3: Connect WebSocket for real-time updates
  const connectWebSocket = () => {
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'welcome_back':
          // Reconnection - get current state
          setProgress(message.progress);
          if (message.tree && message.progress === 100) {
            setTree(message.tree);
            setIsLoading(false);
          }
          break;

        case 'rendering_progress':
          // Progress update
          setProgress(message.progress);
          setStatus('rendering');
          setIsLoading(true);
          break;

        case 'tree_ready':
          // Task completed
          setTree(message.tree);
          setProgress(100);
          setStatus('idle');
          setIsLoading(false);
          break;

        case 'error':
          setError(message.error);
          setStatus('error');
          setIsLoading(false);
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };
  };

  return (
    <div className="chat-page">
      <h1>Chat</h1>

      {/* Progress Bar */}
      {isLoading && (
        <ProgressIndicator progress={progress} />
      )}

      {/* Error Message */}
      {error && (
        <ErrorAlert message={error} onRetry={checkSessionStatus} />
      )}

      {/* Skill Tree Display */}
      {!isLoading && tree && (
        <SkillTreeVisualization tree={tree} />
      )}

      {/* Chat Input */}
      <ChatInput sessionId={sessionId} />
    </div>
  );
};
```

#### 6.2 Progress Indicator Component ⏳
**File:** `frontend/src/modules/chat/components/ProgressIndicator.tsx`

```typescript
interface ProgressIndicatorProps {
  progress: number;
}

export const ProgressIndicator = ({ progress }: ProgressIndicatorProps) => {
  const getStepDescription = (prog: number) => {
    if (prog < 15) return 'Extracting intent...';
    if (prog < 45) return 'Querying documents...';
    if (prog < 75) return 'Rendering tree...';
    return 'Finalizing...';
  };

  return (
    <div className="progress-container">
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="progress-text">
        {getStepDescription(progress)} ({progress}%)
      </p>
    </div>
  );
};
```

#### 6.3 Skill Tree Component 🌳
**File:** `frontend/src/modules/chat/components/SkillTreeVisualization.tsx`

```typescript
import ReactFlow, { 
  Controls, 
  Background,
  MiniMap 
} from 'reactflow';
import 'reactflow/dist/style.css';

interface SkillTreeProps {
  tree: {
    id: string;
    name: string;
    nodes: Array<{
      id: string;
      label: string;
      level: number;
      icon: string;
      status: string;
      resources: Array<any>;
    }>;
    edges: Array<any>;
  };
}

export const SkillTreeVisualization = ({ tree }: SkillTreeProps) => {
  // Convert tree nodes to ReactFlow nodes
  const nodes = tree.nodes.map((node, idx) => ({
    id: node.id,
    data: { 
      label: `${node.icon} ${node.label}`,
      description: node.description || ''
    },
    position: { x: idx * 250, y: node.level * 100 },
  }));

  return (
    <div className="skill-tree-container">
      <h2>{tree.name}</h2>
      <ReactFlow nodes={nodes} edges={tree.edges || []}>
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};
```

#### 6.4 Chat Input Component 📝
**File:** `frontend/src/modules/chat/components/ChatInput.tsx`

```typescript
import { useState } from 'react';

interface ChatInputProps {
  sessionId: string;
}

export const ChatInput = ({ sessionId }: ChatInputProps) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('/api/chat/message-async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: input,
          session_id: sessionId,
          attachments: []
        })
      });

      const data = await response.json();
      
      if (response.status === 202) {
        // Accepted - task queued
        console.log('Task queued:', data.request_id);
        // Frontend will receive updates via WebSocket
        setInput('');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-input-container">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Type your message..."
        disabled={loading}
      />
      <button onClick={handleSend} disabled={loading}>
        {loading ? 'Sending...' : 'Send'}
      </button>
    </div>
  );
};
```

#### 6.5 Error Handler Component ⚠️
**File:** `frontend/src/modules/chat/components/ErrorAlert.tsx`

```typescript
interface ErrorAlertProps {
  message: string;
  onRetry: () => void;
}

export const ErrorAlert = ({ message, onRetry }: ErrorAlertProps) => {
  return (
    <div className="error-alert">
      <p className="error-message">{message}</p>
      <button onClick={onRetry}>Retry</button>
    </div>
  );
};
```

#### 6.6 Custom Hook: useAsyncChat
**File:** `frontend/src/modules/chat/hooks/useAsyncChat.ts`

```typescript
import { useEffect, useState, useCallback } from 'react';

interface ChatState {
  status: 'idle' | 'rendering' | 'error';
  progress: number;
  tree: any | null;
  error: string | null;
  isLoading: boolean;
}

export const useAsyncChat = (sessionId: string) => {
  const [state, setState] = useState<ChatState>({
    status: 'idle',
    progress: 0,
    tree: null,
    error: null,
    isLoading: false
  });

  const checkStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/chat/session/${sessionId}/status`);
      const data = await response.json();

      setState(prev => ({
        ...prev,
        status: data.status,
        progress: data.progress,
        tree: data.tree || null,
        error: data.error || null,
        isLoading: data.status === 'rendering'
      }));

      return data;
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to check status',
        isLoading: false
      }));
    }
  }, [sessionId]);

  useEffect(() => {
    checkStatus();
  }, [sessionId, checkStatus]);

  const sendMessage = useCallback(async (message: string) => {
    try {
      const response = await fetch('/api/chat/message-async', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: message,
          session_id: sessionId
        })
      });

      if (response.status === 202) {
        setState(prev => ({
          ...prev,
          status: 'rendering',
          isLoading: true
        }));
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to send message',
      }));
    }
  }, [sessionId]);

  return {
    ...state,
    checkStatus,
    sendMessage
  };
};
```

#### 6.7 Testing & Validation 🧪

**Test: Chat Component**
```typescript
// frontend/src/modules/chat/pages/__tests__/ChatPage.test.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatPage } from '../ChatPage';

describe('ChatPage', () => {
  it('should display progress while rendering', async () => {
    render(<ChatPage />);

    // Check for progress indicator
    await waitFor(() => {
      expect(screen.getByText(/Extracting intent/i)).toBeInTheDocument();
    });
  });

  it('should display tree when completed', async () => {
    render(<ChatPage />);

    // Wait for tree to display
    await waitFor(() => {
      expect(screen.getByText(/Learning Path/i)).toBeInTheDocument();
    });
  });

  it('should handle errors gracefully', async () => {
    render(<ChatPage />);

    // Check error display
    await waitFor(() => {
      expect(screen.getByText(/Processing failed/i)).toBeInTheDocument();
    });
  });
});
```

#### 6.8 Styling 🎨

**CSS: Chat Styles**
```css
/* frontend/src/modules/chat/styles/chat.css */

.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  gap: 1rem;
  padding: 1rem;
}

.progress-container {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 8px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: #666;
  text-align: center;
}

.skill-tree-container {
  flex: 1;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.error-alert {
  background: #ffebee;
  border-left: 4px solid #f44336;
  padding: 1rem;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-message {
  color: #c62828;
}

.chat-input-container {
  display: flex;
  gap: 0.5rem;
}

.chat-input-container input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.chat-input-container button {
  padding: 0.75rem 1.5rem;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.chat-input-container button:hover {
  background: #45a049;
}
```

### Frontend Checklist ✅

- [ ] ChatPage component receives & displays progress
- [ ] Progress indicator shows 10% → 40% → 70% → 100%
- [ ] WebSocket connects and receives welcome_back event
- [ ] Real-time progress updates display
- [ ] Tree renders when progress = 100%
- [ ] Navigation away/back works correctly
- [ ] GET /status endpoint called on return
- [ ] Error states displayed with retry option
- [ ] Custom hook useAsyncChat working
- [ ] All tests passing
- [ ] CSS styling complete

---

## 🎯 COMPLETE TIMELINE

```
Phase 4: ✅ DONE
├─ GeminiIntentService created
├─ RAGService created
├─ TreeRenderService created
├─ Celery task implemented
└─ API endpoints added

Phase 5: ⏳ NEXT (Backend Integration)
├─ Run migrations (001, 002, 003)
├─ Test GeminiIntentService
├─ Test RAGService
├─ Test TreeRenderService
├─ Test process_chat_intent
├─ Test Redis caching
├─ Test database updates
└─ E2E backend test

Phase 6: 🚀 FINAL (Frontend Integration)
├─ Update ChatPage component
├─ Add ProgressIndicator
├─ Add SkillTreeVisualization
├─ Add ChatInput component
├─ Add ErrorAlert component
├─ Create useAsyncChat hook
├─ Add CSS styling
└─ Frontend testing
```

---

## 📊 SUCCESS METRICS

**Phase 5 Success:**
- ✅ All 3 migrations run successfully
- ✅ All services tests pass
- ✅ Celery task executes 8 steps correctly
- ✅ Database updates persist
- ✅ Redis cache works
- ✅ End-to-end test passes

**Phase 6 Success:**
- ✅ User sends message → 202 response
- ✅ UI shows progress bar (10-100%)
- ✅ User navigates away and returns
- ✅ GET /status retrieves progress
- ✅ WebSocket reconnects and shows state
- ✅ Final tree displays when complete
- ✅ Navigation scenarios all work
- ✅ Error cases handled gracefully

---

## 📝 DELIVERABLES

**Phase 5:**
- 3 database migrations (run successfully)
- Service unit tests (all passing)
- Integration tests (all passing)
- E2E test (all passing)
- Backend ready for production

**Phase 6:**
- 5 React components (ChatPage, ProgressIndicator, SkillTreeVisualization, ChatInput, ErrorAlert)
- 1 custom hook (useAsyncChat)
- CSS styling (responsive & polished)
- Component tests (all passing)
- Frontend ready for production

---

**Ready to start Phase 5? 🚀**
