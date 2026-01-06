# Backend - AI Skill Tree Chat API

Python FastAPI server với RAG (Retrieval-Augmented Generation) chatbot.

## Prerequisites

- Python >= 3.10
- CUDA (optional, cho GPU acceleration)

## Cài đặt

```bash
# Tạo virtual environment (khuyến khích)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Cài dependencies
pip install -r requirements.txt
```

## Cấu hình

Tạo file `.env` với nội dung:

```env
GOOGLE_API_KEY=your_api_key_here
```

## Chạy Server

```bash
python server.py
```

Hoặc với uvicorn:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Server sẽ chạy tại: http://localhost:8000

## API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/health` | GET | Health check |
| `/session/new` | POST | Tạo session mới |
| `/ws` | WebSocket | Chat realtime |

## WebSocket Protocol

### Gửi tin nhắn

```json
{
  "type": "user_message",
  "session_id": "session_xxx",
  "text": "Nội dung tin nhắn"
}
```

### Nhận response

```json
{
  "type": "bot_message",
  "session_id": "session_xxx",
  "text": "Câu trả lời từ AI"
}
```

## Cấu trúc thư mục

```
backend/
├── server.py          # FastAPI server
├── smart_chatbot.py   # Chatbot với RAG
├── requirements.txt   # Python dependencies
└── .env              # Environment variables
```

## ChromaDB

Backend sử dụng ChromaDB từ thư mục `../chroma_db/` để lưu trữ vector embeddings.
