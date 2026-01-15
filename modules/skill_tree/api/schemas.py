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
    status: Optional[str] = "not_started"
    progress_percent: Optional[int] = 0


class ResourceUpdateRequest(BaseModel):
    status: str
    progress_percent: Optional[int] = 0
