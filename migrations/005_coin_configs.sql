CREATE TABLE IF NOT EXISTS coin_configs (
    id UUID PRIMARY KEY,
    feature_key VARCHAR(100) NOT NULL UNIQUE,
    cost INTEGER NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default configurations
INSERT INTO coin_configs (id, feature_key, cost, description, updated_at) VALUES
    (gen_random_uuid(), 'ai_chat', 5, 'Chi phí cho mỗi tin nhắn chat với AI', CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'generate_tree', 10, 'Chi phí tạo một skill tree mới', CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'quiz_attempt', 2, 'Chi phí tham gia một bài trắc nghiệm', CURRENT_TIMESTAMP)
ON CONFLICT (feature_key) DO UPDATE 
SET cost = EXCLUDED.cost, description = EXCLUDED.description, updated_at = EXCLUDED.updated_at;
