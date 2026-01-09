---
trigger: always_on
---

# Backend Architecture (FastAPI + DDD-lite + Clean Architecture)

Kiến trúc này áp dụng cho:
- FastAPI (HTTP / WebSocket)
- AI Chatbot / RAG
- ChromaDB / LLM (Gemini, OpenAI, …)
- Mục tiêu: dễ bảo trì, dễ test, đổi công nghệ không đau

---

## 1. Tổng quan kiến trúc

Client (Web / App)
↓
App Layer (FastAPI)
↓
Use Case Layer
↓
Domain Layer (CORE)
↓
Ports (Interfaces)
↓
Infrastructure (Adapters)

yaml
Copy code

**Nguyên tắc vàng**
- Domain KHÔNG phụ thuộc framework
- FastAPI chỉ là “cửa vào”
- Chroma / Gemini chỉ là adapter

---

## 2. Thư mục `app/` – Framework Layer

👉 Chỉ xử lý **HTTP / WebSocket / DI**

app/
├── main.py
├── api/
│ └── websocket.py
└── deps.py

python
Copy code

### `main.py`
- Bootstrap FastAPI
- Mount router
- Lifecycle (startup / shutdown)

```python
from fastapi import FastAPI
from app.api.websocket import router

app = FastAPI()
app.include_router(router)
api/websocket.py
Nhận message từ client

Gọi usecase

Trả response

python
Copy code
@router.websocket("/chat")
async def chat(ws: WebSocket):
    await ws.accept()
    while True:
        msg = await ws.receive_text()
        reply = await chat_usecase.handle(msg)
        await ws.send_text(reply)
deps.py
Dependency Injection

Wiring port ↔ adapter

python
Copy code
def get_chat_usecase() -> ChatUseCase:
    return ChatUseCase(chatbot_service)
3. Thư mục domain/ – CORE (Quan trọng nhất)
👉 Nơi chứa nghiệp vụ thuần, không import FastAPI, Chroma, Gemini

pgsql
Copy code
domain/
├── entities/
├── ports/
└── services/
3.1 entities/ – Domain Entities
message.py
python
Copy code
@dataclass
class Message:
    role: str   # user | assistant
    content: str
memory.py
python
Copy code
@dataclass
class MemoryItem:
    user_message: str
    bot_reply: str
3.2 ports/ – Interfaces (Hexagonal)
👉 Domain chỉ biết interface, không biết implementation

llm_port.py
python
Copy code
class LLMPort(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
vector_store_port.py
python
Copy code
class VectorStorePort(ABC):
    @abstractmethod
    def search(self, query: str, k: int) -> list[str]:
        pass
memory_port.py
python
Copy code
class MemoryPort(ABC):
    @abstractmethod
    def save(self, user: str, bot: str):
        pass
3.3 services/ – Domain Services
👉 “Não” của hệ thống

chatbot_service.py
python
Copy code
class SmartChatbot:
    def __init__(self, llm, memory, vector_store):
        self.llm = llm
        self.memory = memory
        self.vector_store = vector_store

    async def respond(self, message: str) -> str:
        context = self.vector_store.search(message, k=3)
        prompt = self._build_prompt(context, message)
        answer = await self.llm.generate(prompt)
        self.memory.save(message, answer)
        return answer
4. Thư mục usecases/ – Application Layer
👉 Điều phối luồng nghiệp vụ
👉 Không chứa logic AI chi tiết

Copy code
usecases/
└── chat_usecase.py
python
Copy code
class ChatUseCase:
    def __init__(self, chatbot: SmartChatbot):
        self.chatbot = chatbot

    async def handle(self, user_message: str) -> str:
        return await self.chatbot.respond(user_message)
5. Thư mục infrastructure/ – Adapter Layer
👉 Nơi phụ thuộc công nghệ

wasm
Copy code
infrastructure/
├── llm/
├── vector_store/
├── memory/
└── embeddings/
5.1 LLM Adapter
llm/gemini_adapter.py
python
Copy code
class GeminiAdapter(LLMPort):
    async def generate(self, prompt: str) -> str:
        return gemini.generate_content(prompt)
5.2 Vector Store Adapter
vector_store/chroma_adapter.py
python
Copy code
class ChromaAdapter(VectorStorePort):
    def search(self, query: str, k: int):
        embedding = self.embedder.encode(query)
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )["documents"][0]
5.3 Memory Adapter
memory/sqlite_memory.py
python
Copy code
class SQLiteMemory(MemoryPort):
    def save(self, user: str, bot: str):
        # insert into sqlite
        pass
5.4 Embedding Provider
embeddings/sentence_transformer.py
python
Copy code
class SentenceTransformerEmbedder:
    def encode(self, text: str):
        return self.model.encode(text)
6. Thư mục config/
👉 Quản lý config, env, secret

arduino
Copy code
config/
└── settings.py
python
Copy code
class Settings(BaseSettings):
    GEMINI_API_KEY: str
    CHROMA_PATH: str
7. Thư mục tests/
👉 Test domain không cần FastAPI

pgsql
Copy code
tests/
├── domain/
└── usecases/
8. Quy tắc import (rất quan trọng)
❌ Domain import Infrastructure → SAI
✅ Infrastructure import Domain → ĐÚNG
✅ App import Usecase → ĐÚNG

9. Takeaway
FastAPI là cửa
Domain là não


BE port 8000, FE port 3000

Adapter là tay chân
Đổi tay chân, não không đau