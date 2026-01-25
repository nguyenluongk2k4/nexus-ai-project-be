from pydantic import BaseModel
from typing import Optional

class UploadResponse(BaseModel):
    file_uri: str
    filename: str
    mime_type: str
    display_name: Optional[str] = None
    size_bytes: int
    token_count: int = 0
