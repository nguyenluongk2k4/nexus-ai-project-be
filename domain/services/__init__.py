# Domain Services
# "Brain" of the system - contains pure business logic

from typing import List, Optional
from uuid import UUID

from domain.entities import (
    Message, ChatSession, MessageRole,
    UserSkillTree, UserSkillNode, LearningStatus,
    LearningProgress, StudySession
)
from domain.ports import (
    LLMPort, VectorStorePort,
    ChatRepositoryPort, SkillTreeRepositoryPort, LearningRepositoryPort
)


class ChatbotService:
    """
    Core chatbot service - combines Memory + RAG + AI
    Domain service that orchestrates AI response generation
    """
    
    def __init__(
        self,
        llm: LLMPort,
        vector_store: VectorStorePort,
        chat_repo: ChatRepositoryPort
    ):
        self.llm = llm
        self.vector_store = vector_store
        self.chat_repo = chat_repo
        self.max_context_messages = 10
    
    async def respond(self, session_id: UUID, user_message: str) -> str:
        """
        Generate AI response for user message
        Flow: Search RAG -> Build prompt -> Generate -> Save to memory
        """
        # 1. Search RAG for relevant context
        rag_results = self.vector_store.search(user_message, n_results=3)
        
        # 2. Get conversation history
        history = await self.chat_repo.get_session_messages(
            session_id, 
            limit=self.max_context_messages
        )
        
        # 3. Build prompt with context
        prompt = self._build_prompt(user_message, rag_results, history)
        
        # 4. Generate AI response
        ai_response = await self.llm.generate(prompt)
        
        # 5. Save messages to memory
        await self.chat_repo.add_message(Message(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message
        ))
        await self.chat_repo.add_message(Message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=ai_response
        ))
        
        return ai_response
    
    def _build_prompt(
        self, 
        question: str, 
        rag_results: List[str], 
        history: List[Message]
    ) -> str:
        """Build prompt with conversation history and RAG context"""
        
        # Build history context
        history_context = ""
        if history:
            history_context = "=== LỊCH SỬ CUỘC TRÒ CHUYỆN ===\n"
            for msg in history[-5:]:  # Last 5 messages
                role = "Người dùng" if msg.role == MessageRole.USER else "AI"
                history_context += f"{role}: {msg.content}\n"
            history_context += "=== KẾT THÚC LỊCH SỬ ===\n\n"
        
        # Build RAG context
        rag_context = ""
        if rag_results:
            rag_context = "### Thông tin từ cơ sở kiến thức:\n"
            for i, content in enumerate(rag_results, 1):
                truncated = content[:500] + "..." if len(content) > 500 else content
                rag_context += f"{i}. {truncated}\n"
        
        prompt = f"""Bạn là chuyên gia tư vấn IT Career với khả năng trả lời chính xác, ngắn gọn và có cấu trúc.

{history_context}
{rag_context}

**Câu hỏi:** {question}

**Yêu cầu trả lời:**
- Trả lời NGẮN GỌN, TẬP TRUNG vào vấn đề chính
- Sử dụng Markdown để định dạng
- Cấu trúc: Trả lời trực tiếp → Chi tiết (3-5 điểm) → Lời khuyên
- TRÁNH: Lặp lại câu hỏi, dài dòng

Trả lời:"""
        return prompt


class LearningService:
    """
    Learning progress management service
    Handles skill tree progress, study sessions, recommendations
    """
    
    def __init__(
        self,
        skill_tree_repo: SkillTreeRepositoryPort,
        learning_repo: LearningRepositoryPort
    ):
        self.skill_tree_repo = skill_tree_repo
        self.learning_repo = learning_repo
    
    async def update_node_progress(
        self, 
        user_id: UUID, 
        node_id: UUID, 
        status: LearningStatus,
        progress_percent: int = 0
    ) -> UserSkillNode:
        """Update learning progress for a skill node"""
        
        # Get user's node
        user_tree = await self.skill_tree_repo.get_user_tree(node_id)
        if not user_tree:
            raise ValueError(f"Node {node_id} not found")
        
        # Find and update the node
        for node in user_tree.nodes:
            if node.id == node_id:
                node.status = status
                node.progress_percent = progress_percent
                
                if status == LearningStatus.IN_PROGRESS and not node.started_at:
                    from datetime import datetime
                    node.started_at = datetime.now()
                
                if status == LearningStatus.COMPLETED:
                    from datetime import datetime
                    node.completed_at = datetime.now()
                    node.progress_percent = 100
                
                return await self.skill_tree_repo.update_user_node(node)
        
        raise ValueError(f"Node {node_id} not found in tree")
    
    async def get_learning_stats(self, user_id: UUID) -> dict:
        """Get learning statistics for user"""
        
        # Get all user's trees
        trees = await self.skill_tree_repo.get_user_trees(user_id)
        
        total_nodes = 0
        completed_nodes = 0
        in_progress_nodes = 0
        
        for tree in trees:
            for node in tree.nodes:
                total_nodes += 1
                if node.status == LearningStatus.COMPLETED:
                    completed_nodes += 1
                elif node.status == LearningStatus.IN_PROGRESS:
                    in_progress_nodes += 1
        
        return {
            "total_nodes": total_nodes,
            "completed": completed_nodes,
            "in_progress": in_progress_nodes,
            "not_started": total_nodes - completed_nodes - in_progress_nodes,
            "completion_percent": (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0
        }
    
    async def clone_template_for_user(
        self, 
        template_id: UUID, 
        user_id: UUID
    ) -> UserSkillTree:
        """Clone a skill tree template for user to start learning"""
        return await self.skill_tree_repo.clone_template_to_user(template_id, user_id)


class RecommendationService:
    """
    Recommendation service for jobs and learning paths
    """
    
    def __init__(
        self,
        skill_tree_repo: SkillTreeRepositoryPort,
        learning_repo: LearningRepositoryPort
    ):
        self.skill_tree_repo = skill_tree_repo
        self.learning_repo = learning_repo
    
    async def get_next_skills_to_learn(self, user_id: UUID) -> List[dict]:
        """Recommend next skills based on current progress"""
        
        trees = await self.skill_tree_repo.get_user_trees(user_id)
        recommendations = []
        
        for tree in trees:
            for node in tree.nodes:
                if node.status == LearningStatus.NOT_STARTED:
                    # Check if prerequisites are completed
                    # (would need to check ancestors in closure table)
                    recommendations.append({
                        "node_id": str(node.id),
                        "name": node.name,
                        "tree_name": tree.name
                    })
        
        return recommendations[:5]  # Top 5 recommendations
