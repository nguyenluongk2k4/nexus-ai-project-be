# Chat Module - Domain Service
# Core chatbot logic: RAG + Memory + AI

from typing import List
from uuid import UUID

from modules.chat.domain.entities import Message, MessageRole
from modules.chat.domain.ports import ChatRepositoryPort, LLMPort, VectorStorePort


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
- Chỉ cung cấp thông tin TRỰC TIẾP LIÊN QUAN đến câu hỏi
- Sử dụng Markdown để định dạng:
  • Tiêu đề: ## hoặc ###
  • Danh sách: - hoặc số
  • Nhấn mạnh: **text**
  • Code: ```code```
- Cấu trúc câu trả lời:
  1. Câu trả lời trực tiếp (1-2 câu)
  2. Chi tiết quan trọng (dạng danh sách, tối đa 3-5 điểm)
  3. Lời khuyên/bước tiếp theo (nếu cần, 1-2 câu)
- TRÁNH: Lặp lại câu hỏi, dài dòng, thông tin không liên quan
- Nếu không có thông tin: Nói thẳng và đề xuất hướng tìm hiểu

Trả lời:"""
        return prompt
