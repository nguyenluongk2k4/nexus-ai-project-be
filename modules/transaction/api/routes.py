# Transaction Module - API Routes
# Admin endpoints for transaction management

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from uuid import UUID
import math

from modules.auth.domain.entities import User
from modules.user.api.deps import require_admin
from shared.database.connection import get_db
from .schemas import TransactionResponse, TransactionListResponse


router = APIRouter(prefix="/admin/transactions", tags=["Admin - Transactions"])


@router.get(
    "",
    response_model=TransactionListResponse,
    summary="[Admin] Lấy danh sách giao dịch với phân trang, search, filter, sort"
)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by user name, email, note, transaction_code"),
    type: Optional[str] = Query(None, description="Filter by transaction type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Admin: Get all transactions with pagination, search, filter, and sort
    
    **Available filters:**
    - type: deposit, withdraw, purchase, refund, reward, etc.
    - status: pending, completed, failed, cancelled
    
    **Sortable fields:**
    - created_at, amount, user_name, type, status
    """
    
    # Build WHERE clause
    where_conditions = []
    params = {}
    
    if search:
        where_conditions.append("""
            (u.full_name ILIKE :search 
             OR u.email ILIKE :search 
             OR t.note ILIKE :search
             OR t.transaction_code ILIKE :search)
        """)
        params["search"] = f"%{search}%"
    
    if type:
        where_conditions.append("t.type = :type")
        params["type"] = type
    
    if status:
        where_conditions.append("t.status = :status")
        params["status"] = status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Validate sort_by field to prevent SQL injection
    allowed_sort_fields = {
        "created_at": "t.created_at",
        "amount": "t.amount",
        "user_name": "u.full_name",
        "type": "t.type",
        "status": "t.status"
    }
    sort_field = allowed_sort_fields.get(sort_by, "t.created_at")
    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    
    # Count total records
    count_query = f"""
        SELECT COUNT(*) as total
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        {where_clause}
    """
    count_result = await session.execute(text(count_query), params)
    total = count_result.scalar() or 0
    
    # Calculate pagination
    total_pages = math.ceil(total / page_size)
    offset = (page - 1) * page_size
    
    # Fetch transactions
    query = f"""
        SELECT 
            t.id,
            t.user_id,
            u.full_name as user_name,
            u.email as user_email,
            t.transaction_code,
            t.type,
            t.amount,
            t.balance_before,
            t.balance_after,
            t.status,
            t.note,
            t.created_at
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        {where_clause}
        ORDER BY {sort_field} {sort_direction}
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = page_size
    params["offset"] = offset
    
    result = await session.execute(text(query), params)
    
    transactions = []
    for row in result:
        transactions.append(TransactionResponse(
            id=row.id,
            user_id=row.user_id,
            user_name=row.user_name,
            user_email=row.user_email,
            transaction_code=row.transaction_code,
            type=row.type,
            amount=float(row.amount),
            balance_before=float(row.balance_before) if row.balance_before else 0.0,
            balance_after=float(row.balance_after) if row.balance_after else 0.0,
            status=row.status,
            note=row.note,
            created_at=row.created_at
        ))
    
    return TransactionListResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="[Admin] Lấy chi tiết một giao dịch"
)
async def get_transaction_detail(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Admin: Get transaction details by ID"""
    
    query = """
        SELECT 
            t.id,
            t.user_id,
            u.full_name as user_name,
            u.email as user_email,
            t.transaction_code,
            t.type,
            t.amount,
            t.balance_before,
            t.balance_after,
            t.status,
            t.note,
            t.created_at
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.id = :transaction_id
    """
    
    result = await session.execute(text(query), {"transaction_id": str(transaction_id)})
    row = result.first()
    
    if not row:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    return TransactionResponse(
        id=row.id,
        user_id=row.user_id,
        user_name=row.user_name,
        user_email=row.user_email,
        transaction_code=row.transaction_code,
        type=row.type,
        amount=float(row.amount),
        balance_before=float(row.balance_before) if row.balance_before else 0.0,
        balance_after=float(row.balance_after) if row.balance_after else 0.0,
        status=row.status,
        note=row.note,
        created_at=row.created_at
    )
