"""
Unit tests for GeminiIntentService
Tests intent extraction with Gemini LLM and fallback keyword matching
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.chat.services.gemini_intent_service import GeminiIntentService, Intent
from config.settings import settings


@pytest.fixture
async def intent_service():
    """Create GeminiIntentService instance"""
    return GeminiIntentService()


@pytest.mark.asyncio
class TestGeminiIntentService:
    """Test cases for GeminiIntentService"""
    
    async def test_extract_intent_learning_path(self, intent_service):
        """Test extracting learning path intent"""
        user_message = "I want to learn web development from scratch"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '''{
                "intent": "learning_path",
                "confidence": 0.95,
                "keywords": ["web development", "learn"],
                "reasoning": "User explicitly asks to learn web development"
            }'''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            assert result.intent == Intent.LEARNING_PATH
            assert result.confidence >= 0.9
            assert "web development" in result.keywords
    
    async def test_extract_intent_find_job(self, intent_service):
        """Test extracting job search intent"""
        user_message = "How can I get a job as a Python developer?"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '''{
                "intent": "find_job",
                "confidence": 0.92,
                "keywords": ["job", "python developer"],
                "reasoning": "User asks about job search"
            }'''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            assert result.intent == Intent.FIND_JOB
            assert result.confidence >= 0.85
    
    async def test_extract_intent_practice(self, intent_service):
        """Test extracting practice/exercise intent"""
        user_message = "Give me some coding problems to practice"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '''{
                "intent": "practice",
                "confidence": 0.88,
                "keywords": ["practice", "problems", "coding"],
                "reasoning": "User wants to practice coding"
            }'''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            assert result.intent == Intent.PRACTICE
    
    async def test_extract_intent_resource(self, intent_service):
        """Test extracting resource/documentation intent"""
        user_message = "Where can I find documentation for React?"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '''{
                "intent": "resource",
                "confidence": 0.90,
                "keywords": ["documentation", "React"],
                "reasoning": "User asks for resources"
            }'''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            assert result.intent == Intent.RESOURCE
    
    async def test_extract_intent_general(self, intent_service):
        """Test extracting general intent"""
        user_message = "What's the weather like today?"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = '''{
                "intent": "general",
                "confidence": 0.75,
                "keywords": ["weather"],
                "reasoning": "General off-topic question"
            }'''
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            assert result.intent == Intent.GENERAL
    
    async def test_extract_intent_with_invalid_json_fallback(self, intent_service):
        """Test fallback to keyword matching on invalid JSON"""
        user_message = "I want to learn JavaScript"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_response = MagicMock()
            mock_response.text = "Invalid JSON response"
            mock_model.return_value.generate_content.return_value = mock_response
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            # Should fallback to keyword matching and detect learning_path
            assert result.intent == Intent.LEARNING_PATH
    
    async def test_extract_intent_api_error_fallback(self, intent_service):
        """Test fallback when API call fails"""
        user_message = "I want to learn React"
        
        with patch('modules.chat.services.gemini_intent_service.genai.GenerativeModel') as mock_model:
            mock_model.return_value.generate_content.side_effect = Exception("API Error")
            
            result = await intent_service.extract_intent(user_message)
            
            assert result is not None
            # Should fallback to keyword matching
            assert result.intent in [Intent.LEARNING_PATH, Intent.GENERAL]
    
    async def test_extract_intent_empty_message(self, intent_service):
        """Test handling empty message"""
        user_message = ""
        
        result = await intent_service.extract_intent(user_message)
        
        assert result is not None
        assert result.intent == Intent.GENERAL
        assert result.confidence < 0.5
    
    async def test_extract_intent_none_message(self, intent_service):
        """Test handling None message"""
        user_message = None
        
        result = await intent_service.extract_intent(user_message)
        
        assert result is not None
        assert result.intent == Intent.GENERAL
    
    async def test_keyword_extraction_learning(self, intent_service):
        """Test keyword extraction for learning intent"""
        keywords = intent_service._extract_keywords_by_intent(
            "I want to learn web development",
            Intent.LEARNING_PATH
        )
        
        assert len(keywords) > 0
        # Should contain learning-related keywords
        assert any(keyword in str(keywords).lower() for keyword in ["learn", "web", "development"])
    
    async def test_keyword_extraction_job(self, intent_service):
        """Test keyword extraction for job intent"""
        keywords = intent_service._extract_keywords_by_intent(
            "How can I get a job as a developer",
            Intent.FIND_JOB
        )
        
        assert len(keywords) > 0
        assert any(keyword in str(keywords).lower() for keyword in ["job", "developer"])
    
    async def test_confidence_calculation_high(self, intent_service):
        """Test confidence calculation for clear intent"""
        message = "I want to learn React from beginner to advanced level"
        
        confidence = intent_service._calculate_confidence(
            message,
            Intent.LEARNING_PATH
        )
        
        # Clear learning intent should have high confidence
        assert confidence > 0.7
    
    async def test_confidence_calculation_low(self, intent_service):
        """Test confidence calculation for unclear intent"""
        message = "Hi"
        
        confidence = intent_service._calculate_confidence(
            message,
            Intent.GENERAL
        )
        
        # Short unclear message should have lower confidence
        assert confidence <= 0.7
