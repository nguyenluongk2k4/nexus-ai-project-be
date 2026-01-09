# Chat Module - Domain Ports (Interfaces)

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from modules.chat.domain.entities import ChatSession, Message


class ChatRepositoryPort(ABC):
    """Interface for Chat data access"""
    
    @abstractmethod
    async def get_session(self, session_id: UUID) -> Optional[ChatSession]:
        pass
    
    @abstractmethod
    async def get_user_sessions(self, user_id: UUID) -> List[ChatSession]:
        pass
    
    @abstractmethod
    async def create_session(self, session: ChatSession) -> ChatSession:
        pass
    
    @abstractmethod
    async def add_message(self, message: Message) -> Message:
        pass
    
    @abstractmethod
    async def get_session_messages(self, session_id: UUID, limit: int = 50) -> List[Message]:
        pass
    
    @abstractmethod
    async def get_recent_sessions(self, limit: int = 5, offset: int = 0) -> List[ChatSession]:
        """Get recent sessions with pagination for load more"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and its messages"""
        pass


class LLMPort(ABC):
    """Interface for Language Model interactions"""
    
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str):
        """Generate text as stream"""
        pass


class VectorStorePort(ABC):
    """Interface for Vector Database operations"""
    
    @abstractmethod
    def search(self, query: str, n_results: int = 3) -> List[str]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add documents to vector store"""
        pass
