# NexusAI Backend

FastAPI server với DDD-lite architecture, RAG Chatbot và Skill Tree management.

## 🏗️ Architecture

```
backend/
├── app/                    # Framework Layer (FastAPI)
│   ├── main.py            # Bootstrap, CORS, lifespan
│   ├── deps.py            # Dependency Injection
│   ├── schemas.py         # Pydantic request/response schemas
│   └── api/               # API endpoints
│       ├── admin.py       # Admin CRUD endpoints
│       └── chat.py        # Chat HTTP & WebSocket
│
├── domain/                 # Core Business Logic (NO framework deps)
│   ├── entities/          # Domain entities
│   ├── ports/             # Abstract interfaces (Hexagonal)
│   └── services/          # Domain services
│
├── infrastructure/         # Adapters (implementations)
│   ├── database/          # PostgreSQL/SQLite + SQLAlchemy
│   ├── embeddings/        # SentenceTransformer adapter
│   ├── llm/               # Gemini AI adapter
│   ├── vector_store/      # ChromaDB adapter
│   └── sync/              # Synchronization services
│
├── usecases/              # Application layer (orchestration)
│
└── config/                # Settings & environment
```

## Prerequisites

- Python >= 3.10
- PostgreSQL (hoặc SQLite cho dev)
- CUDA (optional, cho GPU acceleration)

## Cài đặt

```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Cài dependencies
pip install -r requirements.txt
```

## Cấu hình

Copy `.env.example` thành `.env` và điền các giá trị:

```env
# AI
GOOGLE_API_KEY=your_gemini_api_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/nexusai

# ChromaDB
CHROMA_DB_PATH=../chroma_db
```

## Chạy Server

```bash
# Development
python -m app.main

# Hoặc với uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server: http://localhost:8000
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## Seed Data

```bash
python seed_from_json.py
```

## API Endpoints

### Health
| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | API info |
| `/health` | GET | Health check |

### Admin (Skill Tree)
| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/admin/templates` | GET/POST | List/Create skill tree templates |
| `/api/admin/templates/{id}` | GET/PUT/DELETE | CRUD template |
| `/api/admin/skills` | GET/POST | List/Create skills |
| `/api/admin/resources` | GET/POST | List/Create learning resources |

### Chat
| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/chat/session` | POST | Tạo session mới |
| `/api/chat/message` | POST | Gửi message (HTTP) |
| `/api/chat/ws/{session_id}` | WebSocket | Chat realtime |

## WebSocket Protocol

### Gửi tin nhắn
```json
{
  "type": "user_message",
  "text": "Nội dung tin nhắn"
}
```

### Nhận response
```json
{
  "type": "bot_message",
  "text": "Câu trả lời từ AI"
}
```

## Docker

```bash
# Build & run
docker-compose up -d

# Hoặc chỉ build image
docker build -t nexusai-backend .
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL / SQLite |
| ORM | SQLAlchemy (async) |
| Vector DB | ChromaDB |
| LLM | Google Gemini |
| Embeddings | SentenceTransformer (multilingual) |


chroma run --host localhost --port 8001 --path ../chroma_db         

python scripts/sync_chroma_db.py
