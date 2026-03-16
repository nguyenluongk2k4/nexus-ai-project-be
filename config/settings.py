# Config Settings
# Centralized configuration using Pydantic BaseSettings

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App
    APP_NAME: str = "NexusAI"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://nexusai:nexusai_password@localhost:5432/nexusai"
    
    # ChromaDB
    CHROMA_MODE: str = "embedded"  # "embedded" or "server"
    CHROMA_HOST: str = "localhost"  # For server mode
    CHROMA_PORT: int = 8001  # For server mode
    CHROMA_DB_PATH: str = "../chroma_db"  # For embedded mode
    CHROMA_COLLECTION: str = "ksa_project"
    
    # Google AI
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None  # Alias
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    API_BASE_URL: str = "http://localhost:8000" # Base URL for callback construction
    
    # JWT
    JWT_SECRET: str = "khe_nhat_fpt"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    
    # Embedding Model
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # LLM Model
    LLM_MODEL: str = "gemini-2.5-flash"
    SKILL_MATCH_THRESHOLD: float = 0.6

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_FOLDER: str = "nexus_ai/uploads"
    
    # SMTP (Email) Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "nexusai244@gmail.com"
    SMTP_PASSWORD: str = "yhtn myrr sivd yasc"

    # Context Limits
    MAX_FILE_CONTEXT_CHARS: int = 15000  # ~4k tokens, safe for flash model
    FILE_CHUNK_SIZE: int = 2000
    FILE_CHUNK_OVERLAP: int = 200

    # Upload Settings
    UPLOAD_PROVIDER: str = "local" # local | cloudinary
    UPLOAD_DIR: str = "static/uploads"
    UPLOAD_DIR: str = "static/uploads"
    BASE_URL: str = "http://localhost:8000" # For local file links
    
    # Frontend URL for Redirects
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CHAT_DB: int = 2  # Separate DB for chat events
    NOTIFICATION_CHANNEL: str = "notifications"
    
    # Celery & Task Queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_TIMEOUT: int = 300  # 5 minutes
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_SEND_SENT_EVENT: bool = True
    
    # Coin Costs
    COIN_COST_AI_CHAT: int = 5
    COIN_COST_SKILL_TREE_GEN: int = 5
    
    @property
    def gemini_key(self) -> Optional[str]:
        """Get Gemini API key from either env var"""
        return self.GOOGLE_API_KEY or self.GEMINI_API_KEY
    

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export singleton
settings = get_settings()
