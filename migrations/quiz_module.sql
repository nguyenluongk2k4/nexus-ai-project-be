-- =====================================================
-- Quiz Tables Migration
-- Personalized Quiz System with Weakness Analysis
-- =====================================================

-- Quiz Attempts - Lượt thi của user
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES user_skill_nodes(id) ON DELETE CASCADE,
    
    -- Trạng thái: 'generating', 'ready', 'in_progress', 'completed', 'error'
    status VARCHAR(20) DEFAULT 'generating',
    
    -- Điểm số (0-100)
    score FLOAT,
    
    -- Số câu đúng / tổng
    correct_count INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    
    -- Metadata cá nhân hóa: AI params snapshot
    config_snapshot JSONB,
    
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_node ON quiz_attempts(node_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_status ON quiz_attempts(status);

-- Quiz Questions - Câu hỏi AI sinh ra
CREATE TABLE IF NOT EXISTS quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    
    -- Thứ tự câu hỏi (1, 2, 3...)
    order_index INTEGER NOT NULL,
    
    -- Nội dung câu hỏi
    content TEXT NOT NULL,
    
    -- Đáp án dạng JSON: ["A. ...", "B. ...", "C. ...", "D. ..."]
    options JSONB NOT NULL,
    
    -- Index đáp án đúng (0, 1, 2, 3)
    correct_option_index INTEGER NOT NULL,
    
    -- Giải thích
    explanation TEXT,
    
    -- Tag chủ đề để cá nhân hóa
    topic_tag VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_attempt ON quiz_questions(attempt_id);
CREATE INDEX IF NOT EXISTS idx_quiz_questions_topic ON quiz_questions(topic_tag);

-- Quiz Answers - Câu trả lời của user
CREATE TABLE IF NOT EXISTS quiz_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    
    -- User chọn đáp án nào (0, 1, 2, 3)
    selected_option_index INTEGER NOT NULL,
    
    -- Kết quả
    is_correct BOOLEAN DEFAULT FALSE,
    
    -- Thời gian suy nghĩ (giây)
    time_taken_seconds INTEGER,
    
    answered_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(question_id)
);

CREATE INDEX IF NOT EXISTS idx_quiz_answers_question ON quiz_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_quiz_answers_correct ON quiz_answers(is_correct);
