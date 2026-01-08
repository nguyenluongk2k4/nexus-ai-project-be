# Use Cases - Application Layer
# Orchestrates business flows, thin layer over domain services

from typing import List, Optional
from uuid import UUID

from domain.entities import ChatSession, Message, UserSkillTree, LearningProgress
from domain.services import ChatbotService, LearningService


class ChatUseCase:
    """
    Use case for chat interactions
    Orchestrates: receive message -> generate response -> return
    """
    
    def __init__(self, chatbot_service: ChatbotService):
        self.chatbot = chatbot_service
    
    async def handle_message(self, session_id: UUID, user_message: str) -> str:
        """Handle incoming user message and return AI response"""
        if not user_message.strip():
            raise ValueError("Message cannot be empty")
        
        return await self.chatbot.respond(session_id, user_message)
    
    async def create_session(self, user_id: Optional[UUID] = None) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(user_id=user_id)
        return await self.chatbot.chat_repo.create_session(session)
    
    async def get_session_history(self, session_id: UUID, limit: int = 50) -> List[Message]:
        """Get message history for a session"""
        return await self.chatbot.chat_repo.get_session_messages(session_id, limit)


class LearningUseCase:
    """
    Use case for learning progress management
    """
    
    def __init__(self, learning_service: LearningService):
        self.learning = learning_service
    
    async def start_learning_tree(self, user_id: UUID, template_id: UUID) -> UserSkillTree:
        """Clone a skill tree template for user to start learning"""
        return await self.learning.clone_template_for_user(template_id, user_id)
    
    async def update_skill_progress(
        self, 
        user_id: UUID, 
        node_id: UUID, 
        status: str,
        progress: int = 0
    ) -> dict:
        """Update progress on a skill node"""
        from domain.entities import LearningStatus
        
        status_enum = LearningStatus(status)
        node = await self.learning.update_node_progress(
            user_id, node_id, status_enum, progress
        )
        
        return {
            "node_id": str(node.id),
            "status": node.status.value,
            "progress_percent": node.progress_percent
        }
    
    async def get_stats(self, user_id: UUID) -> dict:
        """Get learning statistics for user"""
        return await self.learning.get_learning_stats(user_id)


class AuthUseCase:
    """
    Use case for authentication
    """
    
    def __init__(self, user_repo):
        self.user_repo = user_repo
    
    async def register(self, email: str, username: str, password: str) -> dict:
        """Register a new user"""
        from domain.entities import User
        import bcrypt
        
        # Check if email exists
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        
        # Check if username exists
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise ValueError("Username already taken")
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=password_hash
        )
        
        created = await self.user_repo.create(user)
        
        return {
            "id": str(created.id),
            "email": created.email,
            "username": created.username
        }
    
    async def login(self, email: str, password: str) -> dict:
        """Login user and return token"""
        import bcrypt
        import jwt
        import os
        from datetime import datetime, timedelta
        
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise ValueError("Invalid email or password")
        
        # Generate JWT token
        secret = os.getenv("JWT_SECRET", "your-secret-key")
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username
            }
        }
