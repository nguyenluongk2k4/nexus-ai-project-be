"""
Quiz Generator Adapter - AI-powered quiz question generation using Gemini
"""

import json
import re
from typing import List, Optional, Dict, Any

from shared.llm import GeminiAdapter
from modules.quiz.domain.ports import QuizGeneratorPort, QuestionData


class QuizGeneratorAdapter(QuizGeneratorPort):
    """Generate quiz questions using Gemini AI"""
    
    def __init__(self):
        self.llm = GeminiAdapter()
    
    async def generate_questions(
        self,
        node_name: str,
        node_description: str,
        num_questions: int = 5,
        focus_topics: Optional[List[str]] = None,
        difficulty: str = "medium",
        resources: Optional[List[dict]] = None
    ) -> List[QuestionData]:
        """Generate quiz questions using AI"""
        
        # Build personalized prompt
        focus_instruction = ""
        if focus_topics:
            focus_instruction = f"""
QUAN TRỌNG - CÁ NHÂN HÓA:
Người học này thường sai các chủ đề sau: {', '.join(focus_topics)}
Hãy tập trung {min(3, len(focus_topics))} câu hỏi vào các chủ đề yếu này để giúp họ cải thiện.
Các câu còn lại có thể về các chủ đề khác trong node.
"""
        
        # Build resource context for suggested resources feature
        resource_instruction = ""
        resource_map: Dict[str, str] = {}  # resource_id -> title
        if resources:
            resource_list = []
            for r in resources:
                rid = str(r.get("id", ""))
                title = r.get("title", "Unknown Resource")
                resource_map[rid] = title
                resource_list.append(f"- [{rid}] {title}: {r.get('description', '')[:100]}")
            
            resource_instruction = f"""
TÀI LIỆU HỌC TẬP:
{chr(10).join(resource_list[:10])}

QUAN TRỌNG: Khi tạo câu hỏi, hãy chọn resource phù hợp nhất làm nguồn tham khảo.
Thêm "source_resource_id": "<resource_id>" vào mỗi câu hỏi.
"""
        
        prompt = f"""Bạn là một giáo viên AI chuyên tạo câu hỏi kiểm tra.
        
Hãy tạo {num_questions} câu hỏi trắc nghiệm cho chủ đề sau:
- Tên chủ đề: {node_name}
- Mô tả: {node_description}
- Độ khó: {difficulty}

{focus_instruction}
{resource_instruction}

YÊU CẦU FORMAT - QUAN TRỌNG:
Trả về ĐÚNG JSON array, không có text khác. Mỗi câu hỏi có format:
{{
    "content": "Nội dung câu hỏi",
    "options": ["A. Đáp án A", "B. Đáp án B", "C. Đáp án C", "D. Đáp án D"],
    "correct_option_index": 0,
    "explanation": "Giải thích ngắn gọn tại sao đáp án đúng",
    "topic_tag": "tag ngắn gọn như: syntax, loop, function, security, performance, etc.",
    "source_resource_id": "ID của resource nếu có, hoặc null"
}}

VÍ DỤ OUTPUT:
[
    {{
        "content": "Trong Python, từ khóa nào dùng để định nghĩa hàm?",
        "options": ["A. function", "B. def", "C. func", "D. define"],
        "correct_option_index": 1,
        "explanation": "Python sử dụng từ khóa 'def' để định nghĩa hàm",
        "topic_tag": "function",
        "source_resource_id": null
    }}
]

Chỉ trả về JSON array, không có markdown hay text khác.
"""
        
        try:
            response = await self.llm.generate(prompt)
            
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove ```json and ``` markers
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
            
            # Parse JSON
            questions_data = json.loads(cleaned)
            
            # Convert to QuestionData objects
            questions = []
            for q in questions_data:
                # Get resource info if provided
                source_id = q.get("source_resource_id")
                source_title = None
                if source_id and source_id in resource_map:
                    source_title = resource_map[source_id]
                
                questions.append(QuestionData(
                    content=q["content"],
                    options=q["options"],
                    correct_option_index=q["correct_option_index"],
                    explanation=q.get("explanation", ""),
                    topic_tag=q.get("topic_tag", "general"),
                    source_resource_id=source_id if source_id else None,
                    source_resource_title=source_title
                ))
            
            return questions
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse AI response as JSON: {e}")
            print(f"Response was: {response[:500]}...")
            # Return empty list on parse error
            return []
        except Exception as e:
            print(f"⚠️ Error generating quiz questions: {e}")
            return []


def get_quiz_generator() -> QuizGeneratorAdapter:
    """Factory function to get quiz generator instance"""
    return QuizGeneratorAdapter()
