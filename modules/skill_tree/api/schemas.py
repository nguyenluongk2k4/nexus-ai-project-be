from pydantic import BaseModel
from typing import Optional

class ResourceResponse(BaseModel):
    id: str
    title: str
    url: Optional[str] = None
    type: Optional[str] = None
    platform: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_free: Optional[bool] = None
