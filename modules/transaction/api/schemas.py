# Transaction API Schemas

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    transaction_code: Optional[str]
    type: str
    amount: float
    balance_before: float
    balance_after: float
    status: str
    note: Optional[str]
    created_at: datetime


class TransactionListResponse(BaseModel):
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
