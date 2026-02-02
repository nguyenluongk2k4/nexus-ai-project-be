# Shared LLM Adapter
# Implements LLMPort using Google Gemini

from typing import AsyncGenerator

import google.generativeai as genai

from modules.chat.domain.ports import LLMPort
from config.settings import settings


class GeminiAdapter(LLMPort):
    """Gemini AI adapter implementing LLMPort"""
    
    def __init__(self, model_name: str = None):
        api_key = settings.gemini_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")
        
        model_name = model_name or settings.LLM_MODEL
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
    
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                return "Hệ thống đang bận do quá tải yêu cầu (Gemini Quota), vui lòng thử lại sau giây lát."
            raise RuntimeError(f"Failed to generate content: {e}")
    
    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Generate text as stream"""
        try:
            response = self.model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                yield "Hệ thống đang bận do quá tải yêu cầu, vui lòng thử lại sau giây lát."
                return
            raise RuntimeError(f"Failed to generate stream: {e}")
