# Statistics Module - API Routes
# Admin endpoints for statistics and analytics

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from typing import Optional
from datetime import datetime, date
from uuid import UUID

from modules.auth.domain.entities import User
from modules.user.api.deps import require_admin
from shared.database.connection import get_db
from .schemas import (
    OverviewStatsResponse,
    UserGrowthChartResponse,
    UserGrowthDataPoint,
    SubscriptionChartResponse,
    SubscriptionPlanData,
    TransactionChartResponse,
    TransactionTypeData
)


router = APIRouter(prefix="/admin/statistics", tags=["Admin - Statistics"])


@router.get(
    "/overview",
    response_model=OverviewStatsResponse,
    summary="[Admin] Lấy tổng quan các chỉ số thống kê"
)
async def get_overview_stats(
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Lấy tổng quan các chỉ số thống kê:
    - Tổng số người dùng (không phụ thuộc date range)
    - Số người dùng hoạt động (có last_login_at trong khoảng thời gian)
    - Số người dùng mới (created_at trong khoảng thời gian)
    - Tổng số gói đăng ký (subscription_expires_at > start_date và created_at < end_date)
    - Tổng doanh thu (transactions với status=completed trong khoảng thời gian)
    """
    
    # Tổng số người dùng (không tính khoảng thời gian)
    total_users_query = "SELECT COUNT(*) FROM users"
    total_users_result = await session.execute(text(total_users_query))
    total_users = total_users_result.scalar() or 0
    
    # Build date filter conditions
    date_condition = ""
    date_params = {}
    
    if start_date and end_date:
        date_params["start_date"] = start_date
        date_params["end_date"] = end_date
    elif start_date:
        date_params["start_date"] = start_date
    elif end_date:
        date_params["end_date"] = end_date
    
    # Số người dùng hoạt động (có đăng nhập trong khoảng thời gian)
    active_users_query = "SELECT COUNT(*) FROM users WHERE last_login_at IS NOT NULL"
    if start_date and end_date:
        active_users_query += " AND last_login_at BETWEEN :start_date AND :end_date"
    elif start_date:
        active_users_query += " AND last_login_at >= :start_date"
    elif end_date:
        active_users_query += " AND last_login_at <= :end_date"
    
    active_users_result = await session.execute(text(active_users_query), date_params)
    active_users = active_users_result.scalar() or 0
    
    # Số người dùng mới (created_at trong khoảng thời gian)
    new_users_query = "SELECT COUNT(*) FROM users WHERE 1=1"
    if start_date and end_date:
        new_users_query += " AND created_at BETWEEN :start_date AND :end_date"
    elif start_date:
        new_users_query += " AND created_at >= :start_date"
    elif end_date:
        new_users_query += " AND created_at <= :end_date"
    
    new_users_result = await session.execute(text(new_users_query), date_params)
    new_users = new_users_result.scalar() or 0
    
    # Tổng số gói đăng ký
    # Đếm users có subscription_tier != 'free' và subscription_expires_at còn hiệu lực
    subscriptions_query = """
        SELECT COUNT(*) FROM users 
        WHERE subscription_tier != 'free' 
        AND subscription_expires_at IS NOT NULL
    """
    if start_date:
        subscriptions_query += " AND subscription_expires_at >= :start_date"
    if end_date:
        # Chỉ tính subscription được tạo trước end_date
        subscriptions_query += " AND created_at <= :end_date"
    
    subscriptions_result = await session.execute(text(subscriptions_query), date_params)
    total_subscriptions = subscriptions_result.scalar() or 0
    
    # Tổng doanh thu (từ giao dịch completed trong khoảng thời gian)
    revenue_query = """
        SELECT COALESCE(SUM(amount), 0) FROM transactions 
        WHERE status = 'completed'
        AND type IN ('deposit', 'subscription', 'purchase')
    """
    if start_date and end_date:
        revenue_query += " AND created_at BETWEEN :start_date AND :end_date"
    elif start_date:
        revenue_query += " AND created_at >= :start_date"
    elif end_date:
        revenue_query += " AND created_at <= :end_date"
    
    revenue_result = await session.execute(text(revenue_query), date_params)
    total_revenue = revenue_result.scalar() or 0.0
    
    return OverviewStatsResponse(
        total_users=total_users,
        active_users=active_users,
        new_users=new_users,
        total_subscriptions=total_subscriptions,
        total_revenue=float(total_revenue)
    )


@router.get(
    "/user-growth",
    response_model=UserGrowthChartResponse,
    summary="[Admin] Biểu đồ tăng trưởng người dùng theo ngày"
)
async def get_user_growth_chart(
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Biểu đồ đường thể hiện số người dùng mới đăng ký theo từng ngày
    """
    
    query = """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count
        FROM users
        WHERE 1=1
    """
    
    params = {}
    if start_date and end_date:
        query += " AND DATE(created_at) BETWEEN :start_date AND :end_date"
        params["start_date"] = start_date
        params["end_date"] = end_date
    elif start_date:
        query += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    elif end_date:
        query += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    query += " GROUP BY DATE(created_at) ORDER BY date ASC"
    
    result = await session.execute(text(query), params)
    rows = result.fetchall()
    
    data = [
        UserGrowthDataPoint(
            date=str(row[0]),
            count=row[1]
        )
        for row in rows
    ]
    
    return UserGrowthChartResponse(data=data)


@router.get(
    "/subscription-distribution",
    response_model=SubscriptionChartResponse,
    summary="[Admin] Biểu đồ phân bố gói đăng ký"
)
async def get_subscription_chart(
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Biểu đồ tròn thể hiện phân bố số lượng đăng ký theo từng loại gói
    """
    
    query = """
        SELECT 
            subscription_tier,
            COUNT(*) as count
        FROM users
        WHERE subscription_tier != 'free'
        AND subscription_expires_at IS NOT NULL
    """
    
    params = {}
    if start_date:
        query += " AND subscription_expires_at >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND created_at <= :end_date"
        params["end_date"] = end_date
    
    query += " GROUP BY subscription_tier ORDER BY count DESC"
    
    result = await session.execute(text(query), params)
    rows = result.fetchall()
    
    total = sum(row[1] for row in rows)
    
    data = [
        SubscriptionPlanData(
            plan_name=row[0],
            count=row[1],
            percentage=round((row[1] / total * 100), 2) if total > 0 else 0
        )
        for row in rows
    ]
    
    return SubscriptionChartResponse(data=data, total=total)


@router.get(
    "/transactions-by-type",
    response_model=TransactionChartResponse,
    summary="[Admin] Biểu đồ thống kê giao dịch theo loại"
)
async def get_transaction_chart(
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Biểu đồ cột ghép thể hiện số lượng và tổng giá trị giao dịch theo từng loại
    (deposit, withdraw, purchase, refund, reward, subscription)
    """
    
    query = """
        SELECT 
            type,
            COUNT(*) as count,
            COALESCE(SUM(amount), 0) as total_amount
        FROM transactions
        WHERE status = 'completed'
    """
    
    params = {}
    if start_date and end_date:
        query += " AND DATE(created_at) BETWEEN :start_date AND :end_date"
        params["start_date"] = start_date
        params["end_date"] = end_date
    elif start_date:
        query += " AND DATE(created_at) >= :start_date"
        params["start_date"] = start_date
    elif end_date:
        query += " AND DATE(created_at) <= :end_date"
        params["end_date"] = end_date
    
    query += " GROUP BY type ORDER BY total_amount DESC"
    
    result = await session.execute(text(query), params)
    rows = result.fetchall()
    
    data = [
        TransactionTypeData(
            type=row[0],
            count=row[1],
            total_amount=float(row[2])
        )
        for row in rows
    ]
    
    return TransactionChartResponse(data=data)
