# Main FastAPI Application
# Bootstrap, mount routers, configure Swagger

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# Import from modular DDD structure
from modules.chat.api.routes import router as chat_router
from modules.admin.api.routes import router as admin_router
from modules.auth.api.routes import router as auth_router
# Skill Tree Router
from modules.skill_tree.api.routes import router as skill_tree_router
# Forum Router
from modules.forum.api.router import router as forum_router
# Profile Router
from modules.profile.api.routes import router as profile_router
# Purchase Router
from modules.purchase.api.routes import router as purchase_router
# Subscription Router
from modules.subscription.api.routes import router as subscription_router
# Timeline Router
from modules.timeline.api.routes import router as timeline_router
# Shared database
from shared.database.connection import init_db
from shared.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__, "SYSTEM")


# ============================================================
# LIFESPAN (startup/shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    logger.info("Starting NexusAI Backend...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Pre-load AI models
    try:
        from modules.chat.providers import get_llm, get_vector_store
        get_llm()
        logger.info("LLM model loaded")
        
        vector_store = get_vector_store()
        doc_count = vector_store.collection.count()
        logger.info(f"Vector store loaded: {doc_count} documents in ChromaDB")
    except Exception as e:
        logger.warning(f"Could not pre-load models: {e}")
    
    logger.info("NexusAI Backend ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NexusAI Backend...")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="NexusAI API",
    description="""
# NexusAI - AI-powered Learning Platform API

## Features
- 🤖 **AI Chatbot** - RAG-enhanced chatbot với Gemini AI
- 🌳 **Skill Tree** - Quản lý cây kỹ năng với closure table
- 📚 **Learning Progress** - Theo dõi tiến độ học tập
- 💬 **Forum** - Diễn đàn thảo luận
- 💼 **Jobs** - Gợi ý việc làm dựa trên skills

## Architecture
- **Backend**: FastAPI + SQLAlchemy (PostgreSQL/SQLite)
- **Vector DB**: ChromaDB for RAG
- **AI**: Google Gemini + SentenceTransformer

## Authentication
Sử dụng JWT Bearer token cho các protected endpoints.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS (from modules/)
# ============================================================

app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

app.include_router(skill_tree_router, prefix="/api")
app.include_router(forum_router)  # Already has /api/forum prefix
app.include_router(profile_router, prefix="/api")
app.include_router(purchase_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")
app.include_router(timeline_router)  # Already has /api/timeline prefix


# ============================================================
# ROOT ENDPOINTS
# ============================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API info"""
    return {
        "name": "NexusAI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# ============================================================
# CUSTOM OPENAPI SCHEMA (for better Swagger)
# ============================================================

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="NexusAI API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from /api/auth/login"
        }
    }
    
    # Add global security requirement - this makes Swagger show Authorize button
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    # Add tags metadata
    openapi_schema["tags"] = [
        {
            "name": "Health",
            "description": "Health check endpoints"
        },
        {
            "name": "Admin",
            "description": "Admin CRUD operations for skills, templates, resources"
        },
        {
            "name": "Chat",
            "description": "AI Chatbot endpoints (HTTP & WebSocket)"
        },
        {
            "name": "Learning",
            "description": "Learning progress and timeline management"
        },
        {
            "name": "Forum",
            "description": "Forum posts and comments"
        },
        {
            "name": "Jobs",
            "description": "Job listings and recommendations"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================
# RUN (for development)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    # Log configuration will be called again in lifespan, but good to have here too if running directly
    # Note: re-configure might duplicate handlers if not handled in configure_logging
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

