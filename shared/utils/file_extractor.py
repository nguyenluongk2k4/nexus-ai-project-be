
import httpx
import io
import logging
from typing import Optional
from pypdf import PdfReader

logger = logging.getLogger(__name__)

async def extract_text_from_url(url: str, mime_type: str = "") -> str:
    """
    Download file from URL and extract text content.
    Supports: PDF, Text
    """
    if not url:
        return ""
        
    from config.settings import settings
    import os
    import aiofiles

    try:
        content = b""
        # Optimization: Read local files directly to avoid loopback request deadlock
        if settings.UPLOAD_PROVIDER == "local" and settings.BASE_URL in url and "/static/uploads/" in url:
             logger.info(f"Detected local file URL: {url}, reading from disk...")
             # Extract relative path
             # URL: http://localhost:8000/static/uploads/file.pdf
             # REL: /static/uploads/file.pdf
             rel_path = url.replace(settings.BASE_URL, "")
             if rel_path.startswith("/"):
                 rel_path = rel_path[1:]
             
             # Map /static/uploads to actual directory
             # settings.UPLOAD_DIR is "static/uploads"
             # So plain join works if structured correctly
             # rel_path is "static/uploads/file.pdf"
             # but we want relative to CWD?
             # settings.UPLOAD_DIR is typically relative to CWD.
             
             local_path = os.path.join(os.getcwd(), rel_path)
             
             if os.path.exists(local_path):
                 async with aiofiles.open(local_path, 'rb') as f:
                     content = await f.read()
             else:
                 logger.warning(f"Local file not found at {local_path}, falling back to HTTP")
        
        if not content:
             headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
             }
             async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                content = response.content
            
        content_type = mime_type or response.headers.get("content-type", "")
        
        if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
            return _extract_pdf(content)
        elif "text" in content_type.lower() or "json" in content_type.lower():
             return content.decode('utf-8', errors='ignore')
        else:
            # For images or other binaries, we can't extract text easily without OCR.
            # Returning empty string or maybe a placeholder.
            # If using multimodal LLM, we should pass image data, but current LLMPort is text-only.
            logger.info(f"Skipping text extraction for non-text type: {content_type}")
            return ""

    except Exception as e:
        logger.error(f"Failed to extract text from {url}: {e}")
        return f"[Error downloading/reading file: {str(e)}]"

def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return "[Error extracting PDF text]"
