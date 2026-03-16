from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CoinPackageCreateRequest(BaseModel):
    id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    coin_amount: int = Field(gt=0)
    bonus_amount: int = Field(default=0, ge=0)
    badge_color: str = Field(default="#8B5CF6", min_length=1, max_length=20)
    is_popular: bool = False
    display_order: int = Field(default=0, ge=0)


class CoinPackageResponse(BaseModel):
    id: str
    name: str
    price: float
    coin_amount: int
    bonus_amount: int
    badge_color: str
    is_popular: bool
    is_active: bool
    display_order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
