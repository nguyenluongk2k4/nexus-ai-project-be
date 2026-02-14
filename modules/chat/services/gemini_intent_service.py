# Chat Module - Gemini Intent Service
# Extracts user intent from message using Gemini LLM

import json
import logging
from typing import Dict, Optional
from shared.llm.gemini_adapter import GeminiAdapter

logger = logging.getLogger(__name__)


class GeminiIntentService:
    """
    Service to extract user intent from messages using Gemini LLM
    
    Supported intents:
    - learning_path: User wants to learn something new
    - find_job: User looking for job/career opportunities
    - practice: User wants to practice skills
    - resource: User looking for learning resources
    - general: General conversation
    """
    
    def __init__(self, llm_adapter: Optional[GeminiAdapter] = None):
        """
        Initialize service with LLM adapter
        
        Args:
            llm_adapter: GeminiAdapter instance (creates new if None)
        """
        self.llm = llm_adapter or GeminiAdapter()
        self.intent_keywords = {
            "learning_path": ["học", "tìm hiểu", "muốn biết", "cách học", "bắt đầu", "từ đầu", "cơ bản"],
            "find_job": ["công việc", "job", "việc làm", "tuyển dụng", "nhận việc", "kiếm ngành"],
            "practice": ["luyện", "bài tập", "thực hành", "practice", "làm bài", "practice"],
            "resource": ["tài liệu", "nguồn", "đường dẫn", "link", "resource", "materials"],
        }
    
    async def extract_intent(self, user_message: str) -> Dict[str, any]:
        """
        Extract intent from user message using Gemini
        
        Args:
            user_message: User's text message
        
        Returns:
            {
                "intent": "learning_path|find_job|practice|resource|general",
                "keywords": ["keyword1", "keyword2", ...],
                "confidence": 0.0-1.0,
                "reasoning": "explanation"
            }
        """
        try:
            logger.info(f"🧠 Extracting intent from: {user_message[:100]}")
            
            # Build prompt for intent extraction
            prompt = self._build_intent_prompt(user_message)
            
            # Call Gemini API
            response = await self.llm.generate(prompt)
            
            # Parse response
            result = self._parse_gemini_response(response, user_message)
            
            logger.info(f"✅ Intent extracted: {result['intent']} (confidence: {result['confidence']})")
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to extract intent: {e}", exc_info=True)
            # Return default intent on error
            return {
                "intent": "general",
                "keywords": self._extract_keywords(user_message),
                "confidence": 0.5,
                "reasoning": "Default intent due to processing error"
            }
    
    def _build_intent_prompt(self, user_message: str) -> str:
        """Build prompt for Gemini to classify intent"""
        return f"""Analyze the following user message and extract the intent and keywords.

User message: "{user_message}"

Respond in JSON format with:
- intent: one of "learning_path", "find_job", "practice", "resource", or "general"
- keywords: list of extracted keywords (3-5 words)
- confidence: confidence score (0.0-1.0)
- reasoning: brief explanation (1 sentence)

Focus on:
- "learning_path": User wants to learn a new skill or topic
- "find_job": User looking for job opportunities or career guidance
- "practice": User wants to practice or do exercises
- "resource": User looking for learning materials or links
- "general": Anything else

Return ONLY valid JSON, no other text."""
    
    def _parse_gemini_response(self, response: str, original_message: str) -> Dict[str, any]:
        """Parse Gemini response and extract intent"""
        try:
            # Try to extract JSON from response
            json_str = response.strip()
            
            # Handle markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            parsed = json.loads(json_str.strip())
            
            # Validate response
            if "intent" not in parsed:
                parsed["intent"] = "general"
            
            if "keywords" not in parsed:
                parsed["keywords"] = self._extract_keywords(original_message)
            
            if "confidence" not in parsed:
                parsed["confidence"] = 0.7
            
            # Ensure intent is valid
            valid_intents = ["learning_path", "find_job", "practice", "resource", "general"]
            if parsed.get("intent") not in valid_intents:
                parsed["intent"] = "general"
            
            return {
                "intent": parsed.get("intent", "general"),
                "keywords": parsed.get("keywords", [])[:5],  # Limit to 5 keywords
                "confidence": float(parsed.get("confidence", 0.5)),
                "reasoning": parsed.get("reasoning", "")
            }
        
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ Failed to parse Gemini response: {e}")
            # Fallback to keyword-based intent detection
            return self._keyword_based_intent(original_message)
    
    def _keyword_based_intent(self, user_message: str) -> Dict[str, any]:
        """Fallback keyword-based intent extraction"""
        message_lower = user_message.lower()
        keywords = self._extract_keywords(message_lower)
        
        # Count matching keywords for each intent
        intent_scores = {}
        for intent, keywords_list in self.intent_keywords.items():
            matches = sum(1 for kw in keywords_list if kw in message_lower)
            intent_scores[intent] = matches
        
        # Get intent with highest score
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent] / len(self.intent_keywords.get(best_intent, [1]))
        
        return {
            "intent": best_intent if intent_scores[best_intent] > 0 else "general",
            "keywords": keywords,
            "confidence": min(confidence, 1.0),
            "reasoning": f"Detected from keywords: {', '.join(keywords)}"
        }
    
    def _extract_keywords(self, user_message: str) -> list:
        """Extract keywords from user message"""
        # Simple keyword extraction: split by common words and symbols
        import re
        
        # Remove special characters and split
        words = re.split(r'[^\w\u0100-\uffff]+', user_message.lower())
        
        # Filter empty and common words
        stop_words = {"và", "hoặc", "từ", "để", "là", "cái", "này", "đó", "và", "hoặc", "the", "a", "an", "is", "are"}
        keywords = [w for w in words if len(w) > 2 and w not in stop_words][:5]
        
        return keywords
