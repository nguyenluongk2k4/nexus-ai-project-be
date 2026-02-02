"""
Quiz SQLAlchemy Models
Lưu trữ lịch sử quiz để hỗ trợ cá nhân hóa
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Boolean, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from shared.database import Base


class QuizAttempt(Base):
    """
    Lưu trữ mỗi lần user nhấn 'Take Quiz'.
    Mỗi lần là một đề khác nhau do AI sinh ra.
    """
    __tablename__ = "quiz_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    node_id = Column(UUID(as_uuid=True), ForeignKey("user_skill_nodes.id"), nullable=False)
    
    # Trạng thái: 'generating', 'ready', 'in_progress', 'completed'
    status = Column(String(20), default="generating")
    
    # Điểm số (0-100)
    score = Column(Float, nullable=True)
    
    # Số câu đúng / tổng câu
    correct_count = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    
    # Metadata cá nhân hóa: AI đã dùng tham số gì để tạo quiz này?
    # VD: { "focus_topics": ["memory_management"], "difficulty": "hard" }
    config_snapshot = Column(JSON, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    questions = relationship("QuizQuestion", back_populates="attempt", cascade="all, delete-orphan")


class QuizQuestion(Base):
    """
    Lưu câu hỏi AI sinh ra.
    Tại sao phải lưu? Để người dùng có thể xem lại (Review) 
    và để hệ thống biết user yếu mảng nào.
    """
    __tablename__ = "quiz_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey("quiz_attempts.id"), nullable=False)
    
    # Thứ tự câu hỏi trong quiz (1, 2, 3...)
    order_index = Column(Integer, nullable=False)
    
    # Nội dung câu hỏi
    content = Column(Text, nullable=False)
    
    # Lưu danh sách đáp án dạng JSON: ["A. ...", "B. ...", "C. ...", "D. ..."]
    options = Column(JSON, nullable=False)
    
    # Index của đáp án đúng (0, 1, 2, 3)
    correct_option_index = Column(Integer, nullable=False)
    
    # Giải thích tại sao đúng (quan trọng để học)
    explanation = Column(Text, nullable=True)
    
    # TAG QUAN TRỌNG ĐỂ CÁ NHÂN HÓA
    # VD: "syntax", "logic", "security", "performance"
    # Nếu user sai nhiều câu có tag "security", lần sau AI sẽ hỏi nhiều về security hơn.
    topic_tag = Column(String(100), nullable=True)
    
    # SOURCE RESOURCE - Để gợi ý user xem lại khi trả lời sai
    # Nếu AI sinh câu hỏi từ một resource cụ thể, lưu ID của resource đó
    source_resource_id = Column(UUID(as_uuid=True), nullable=True)
    source_resource_title = Column(String(500), nullable=True)
    
    # Relationships
    attempt = relationship("QuizAttempt", back_populates="questions")
    user_answer = relationship("QuizAnswer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class QuizAnswer(Base):
    """
    Lưu câu trả lời của user cho từng câu hỏi
    """
    __tablename__ = "quiz_answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id"), nullable=False)
    
    # User chọn đáp án nào (0, 1, 2, 3)
    selected_option_index = Column(Integer, nullable=False)
    
    # Kết quả
    is_correct = Column(Boolean, default=False)
    
    # Thời gian user suy nghĩ (giây)
    # Nếu quá nhanh -> Đoán bừa. Quá lâu -> Khó hiểu.
    time_taken_seconds = Column(Integer, nullable=True)
    
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    question = relationship("QuizQuestion", back_populates="user_answer")
