# Statistics API Schemas

from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime


class OverviewStatsResponse(BaseModel):
    """Tổng quan các chỉ số thống kê"""
    total_users: int
    active_users: int
    new_users: int
    total_subscriptions: int
    total_revenue: float


class UserGrowthDataPoint(BaseModel):
    """Điểm dữ liệu cho biểu đồ tăng trưởng người dùng"""
    date: str  # YYYY-MM-DD format
    count: int


class UserGrowthChartResponse(BaseModel):
    """Dữ liệu biểu đồ tăng trưởng người dùng theo ngày"""
    data: List[UserGrowthDataPoint]


class SubscriptionPlanData(BaseModel):
    """Dữ liệu số lượng đăng ký theo từng plan"""
    plan_name: str
    count: int
    percentage: float


class SubscriptionChartResponse(BaseModel):
    """Dữ liệu biểu đồ phân bố gói đăng ký (pie chart)"""
    data: List[SubscriptionPlanData]
    total: int


class TransactionTypeData(BaseModel):
    """Dữ liệu số lượng và giá trị giao dịch theo loại"""
    type: str
    count: int
    total_amount: float


class TransactionChartResponse(BaseModel):
    """Dữ liệu biểu đồ giao dịch theo loại (bar chart)"""
    data: List[TransactionTypeData]
