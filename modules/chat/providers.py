# Chat Module - Providers (Dependency Injection)
# Wiring domain services with infrastructure adapters

from functools import lru_cache

from modules.chat.domain.services import ChatbotService
from modules.chat.infrastructure.repository import ChatRepositoryImpl


@lru_cache()
def get_llm():
    """Get LLM adapter (singleton)"""
    from shared.llm.gemini_adapter import GeminiAdapter
    return GeminiAdapter()


@lru_cache()
def get_vector_store():
    """Get vector store adapter (singleton)"""
    from shared.vector_store.chroma_adapter import ChromaAdapter
    return ChromaAdapter()


def get_chat_repository():
    """Get chat repository instance"""
    return ChatRepositoryImpl()


def get_chatbot_service() -> ChatbotService:
    """Get chatbot service with all dependencies wired"""
    return ChatbotService(
        llm=get_llm(),
        vector_store=get_vector_store(),
        chat_repo=get_chat_repository()
    )
