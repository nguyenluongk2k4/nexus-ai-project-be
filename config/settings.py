# Config Settings
# Centralized configuration using Pydantic BaseSettings

import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
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
    
    # JWT
    JWT_SECRET: str = "khe_nhat_fpt"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    
    # Embedding Model
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # LLM Model
    LLM_MODEL: str = "gemini-2.5-flash"
    SKILL_MATCH_THRESHOLD: float = 0.6
    
    @property
    def gemini_key(self) -> Optional[str]:
        """Get Gemini API key from either env var"""
        return self.GOOGLE_API_KEY or self.GEMINI_API_KEY
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export singleton
settings = get_settings()
