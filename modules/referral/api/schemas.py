from pydantic import BaseModel
from typing import List
from datetime import datetime


class ApplyReferralRequest(BaseModel):
    code: str


class ApplyReferralResponse(BaseModel):
    success: bool
    message: str
    coins_awarded: int


class ReferralHistoryItemResponse(BaseModel):
    referee_id: str
    status: str
    date: str


class ReferralStatsResponse(BaseModel):
    my_code: str
    total_invited: int
    total_earned: int
    history: List[ReferralHistoryItemResponse]
