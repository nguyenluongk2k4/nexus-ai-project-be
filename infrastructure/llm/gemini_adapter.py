# Infrastructure - LLM Adapter
# Implements LLMPort using Google Gemini

import os
from typing import AsyncGenerator
from dotenv import load_dotenv

import google.generativeai as genai

from domain.ports import LLMPort

load_dotenv()


class GeminiAdapter(LLMPort):
    """
    Gemini AI adapter implementing LLMPort
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
    
    async def generate(self, prompt: str) -> str:
        """Generate text from prompt"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to generate content: {e}")
    
    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Generate text as stream"""
        try:
            response = self.model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise RuntimeError(f"Failed to generate stream: {e}")
