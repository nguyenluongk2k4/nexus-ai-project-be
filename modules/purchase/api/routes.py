# Purchase Module - API Routes
# Endpoints for payment/top-up with SePay integration

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4
import secrets
import hashlib
import hmac

from modules.auth.api.deps import get_current_user, get_current_user_id
from modules.auth.domain.entities import User
from shared.database.connection import get_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/purchase", tags=["Purchase"])


# ============================================================
# SCHEMAS
# ============================================================

class CreateTransactionRequest(BaseModel):
    amount: int  # Amount in VND


class TransactionResponse(BaseModel):
    id: str
    transaction_code: str
    amount: int
    status: str
    qr_url: str
    bank_name: str
    account_number: str
    account_name: str
    transfer_content: str
    expires_at: datetime
    created_at: datetime


class TransactionStatusResponse(BaseModel):
    transaction_code: str
    status: str  # pending, completed, failed, expired
    amount: int
    completed_at: Optional[datetime] = None


class TransactionHistoryItem(BaseModel):
    id: str
    type: str
    amount: float
    status: str
    transaction_code: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    note: Optional[str]


class SePayWebhookPayload(BaseModel):
    """SePay webhook payload structure"""
    id: int
    gateway: str
    transactionDate: str
    accountNumber: str
    subAccount: Optional[str] = None
    code: Optional[str] = None
    content: str
    transferType: str
    description: str
    transferAmount: int
    referenceCode: str
    accumulated: int


# ============================================================
# CONFIG
# ============================================================

# SePay config - should be in .env
SEPAY_BANK_NAME = "TP Bank"
SEPAY_ACCOUNT_NUMBER = "12524042004"
SEPAY_ACCOUNT_NAME = "NEXUS AI"
SEPAY_QR_TEMPLATE = "https://qr.sepay.vn/img?acc={account}&bank=TPBank&amount={amount}&des={content}"
SEPAY_WEBHOOK_SECRET = ""  # Set in .env for production

# Transaction expiry time
TRANSACTION_EXPIRY_MINUTES = 30


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_transaction_code() -> str:
    """Generate unique transaction code for transfer content"""
    random_part = secrets.token_hex(4).upper()
    return f"NEXUS{random_part}"


def generate_qr_url(amount: int, content: str) -> str:
    """Generate SePay QR code URL"""
    return SEPAY_QR_TEMPLATE.format(
        account=SEPAY_ACCOUNT_NUMBER,
        amount=amount,
        content=content
    )


# ============================================================
# ENDPOINTS
# ============================================================

@router.post(
    "/create",
    response_model=TransactionResponse,
    summary="Tạo giao dịch nạp tiền mới"
)
async def create_transaction(
    data: CreateTransactionRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create a new pending deposit transaction"""
    
    if data.amount < 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền tối thiểu là 10,000 VNĐ"
        )
    
    if data.amount > 50000000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền tối đa là 50,000,000 VNĐ"
        )
    
    # Generate unique transaction code
    transaction_code = generate_transaction_code()
    transaction_id = uuid4()
    expires_at = datetime.now() + timedelta(minutes=TRANSACTION_EXPIRY_MINUTES)
    
    # Get user's current balance
    balance_result = await session.execute(
        text("SELECT COALESCE(balance, 0) FROM users WHERE id = :user_id"),
        {"user_id": str(user.id)}
    )
    current_balance = float(balance_result.scalar() or 0)
    
    # Create pending transaction
    await session.execute(
        text("""
            INSERT INTO transactions (
                id, user_id, type, amount, 
                balance_before, balance_after,
                transaction_code, payment_method, status,
                created_at, expires_at
            ) VALUES (
                :id, :user_id, 'deposit', :amount,
                :balance_before, :balance_after,
                :code, 'sepay_qr', 'pending',
                NOW(), :expires_at
            )
        """),
        {
            "id": str(transaction_id),
            "user_id": str(user.id),
            "amount": data.amount,
            "balance_before": current_balance,
            "balance_after": current_balance + data.amount,
            "code": transaction_code,
            "expires_at": expires_at
        }
    )
    await session.commit()
    
    # Generate QR URL
    qr_url = generate_qr_url(data.amount, transaction_code)
    
    return TransactionResponse(
        id=str(transaction_id),
        transaction_code=transaction_code,
        amount=data.amount,
        status="pending",
        qr_url=qr_url,
        bank_name=SEPAY_BANK_NAME,
        account_number=SEPAY_ACCOUNT_NUMBER,
        account_name=SEPAY_ACCOUNT_NAME,
        transfer_content=transaction_code,
        expires_at=expires_at,
        created_at=datetime.now()
    )


@router.post(
    "/webhook/sepay",
    summary="SePay webhook callback",
    include_in_schema=False  # Hide from Swagger
)
async def sepay_webhook(
    payload: SePayWebhookPayload,
    request: Request,
    session: AsyncSession = Depends(get_db)
):
    """
    SePay webhook callback when payment is received.
    SePay will call this endpoint when money is transferred.
    """
    
    # Optional: Verify webhook signature
    # signature = request.headers.get("X-Sepay-Signature")
    # if SEPAY_WEBHOOK_SECRET and not verify_signature(payload, signature):
    #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Extract transaction code from transfer content
    # Content might be: "NEXUS731E4213 Ma giao dich Trace251897"
    # We need to find the NEXUS... pattern
    import re
    content = payload.content.upper()
    
    # Find NEXUS followed by 8 hex characters
    match = re.search(r'NEXUS[A-F0-9]{8}', content)
    if not match:
        return {"status": "ignored", "reason": "no_nexus_code_found"}
    
    transaction_code = match.group(0)
    
    # Find matching pending transaction
    result = await session.execute(
        text("""
            SELECT id, user_id, amount, balance_after
            FROM transactions
            WHERE transaction_code = :code
            AND status = 'pending'
            AND expires_at > NOW()
        """),
        {"code": transaction_code}
    )
    transaction = result.fetchone()
    
    if not transaction:
        # No matching transaction found - might be manual transfer
        # Could log this for manual review
        return {"status": "ignored", "reason": "no_matching_transaction"}
    
    # Verify amount matches
    if payload.transferAmount < transaction.amount:
        return {"status": "ignored", "reason": "amount_mismatch"}
    
    # Update transaction to completed
    await session.execute(
        text("""
            UPDATE transactions
            SET status = 'completed',
                completed_at = NOW(),
                updated_at = NOW(),
                bank_reference = :bank_ref,
                note = :note
            WHERE id = :id
        """),
        {
            "id": str(transaction.id),
            "bank_ref": payload.referenceCode,
            "note": f"Received from {payload.gateway}: {payload.description}"
        }
    )
    
    # Update user balance
    await session.execute(
        text("""
            UPDATE users
            SET balance = COALESCE(balance, 0) + :amount
            WHERE id = :user_id
        """),
        {
            "amount": transaction.amount,
            "user_id": str(transaction.user_id)
        }
    )
    
    await session.commit()
    
    return {"status": "success", "transaction_id": str(transaction.id)}


@router.get(
    "/status/{transaction_code}",
    response_model=TransactionStatusResponse,
    summary="Kiểm tra trạng thái giao dịch"
)
async def check_transaction_status(
    transaction_code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Check transaction status (for polling from frontend)"""
    
    result = await session.execute(
        text("""
            SELECT transaction_code, status, amount, completed_at
            FROM transactions
            WHERE transaction_code = :code
            AND user_id = :user_id
        """),
        {"code": transaction_code, "user_id": str(user.id)}
    )
    transaction = result.fetchone()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy giao dịch"
        )
    
    # Check if expired
    status_value = transaction.status
    if status_value == "pending":
        expires_check = await session.execute(
            text("""
                SELECT 1 FROM transactions
                WHERE transaction_code = :code
                AND expires_at < NOW()
            """),
            {"code": transaction_code}
        )
        if expires_check.fetchone():
            # Mark as expired
            await session.execute(
                text("UPDATE transactions SET status = 'expired' WHERE transaction_code = :code"),
                {"code": transaction_code}
            )
            await session.commit()
            status_value = "expired"
    
    return TransactionStatusResponse(
        transaction_code=transaction.transaction_code,
        status=status_value,
        amount=int(transaction.amount),
        completed_at=transaction.completed_at
    )


@router.get(
    "/history",
    response_model=list[TransactionHistoryItem],
    summary="Lấy lịch sử giao dịch"
)
async def get_transaction_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """Get user's transaction history"""
    
    result = await session.execute(
        text("""
            SELECT id, type, amount, status, transaction_code, 
                   created_at, completed_at, note
            FROM transactions
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"user_id": str(user.id), "limit": limit, "offset": offset}
    )
    
    transactions = []
    for row in result.fetchall():
        transactions.append(TransactionHistoryItem(
            id=str(row.id),
            type=row.type,
            amount=float(row.amount),
            status=row.status,
            transaction_code=row.transaction_code,
            created_at=row.created_at,
            completed_at=row.completed_at,
            note=row.note
        ))
    
    return transactions


@router.get(
    "/balance",
    summary="Lấy số dư hiện tại"
)
async def get_balance(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user's current balance"""
    
    result = await session.execute(
        text("SELECT COALESCE(balance, 0) FROM users WHERE id = :user_id"),
        {"user_id": str(user.id)}
    )
    balance = float(result.scalar() or 0)
    
    return {"balance": balance}


# ============================================================
# RESUME PENDING TRANSACTION
# ============================================================

@router.get(
    "/resume/{transaction_code}",
    response_model=TransactionResponse,
    summary="Lấy thông tin giao dịch đang chờ để tiếp tục thanh toán"
)
async def get_pending_transaction(
    transaction_code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get pending transaction details to resume payment"""
    
    result = await session.execute(
        text("""
            SELECT id, transaction_code, amount, status, created_at, expires_at
            FROM transactions
            WHERE transaction_code = :code
            AND user_id = :user_id
            AND status = 'pending'
        """),
        {"code": transaction_code, "user_id": str(user.id)}
    )
    transaction = result.fetchone()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy giao dịch hoặc đã hết hạn"
        )
    
    # Check if expired
    if transaction.expires_at and transaction.expires_at < datetime.now():
        # Mark as expired
        await session.execute(
            text("UPDATE transactions SET status = 'expired' WHERE id = :id"),
            {"id": str(transaction.id)}
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dịch đã hết hạn"
        )
    
    # Generate QR URL
    qr_url = generate_qr_url(int(transaction.amount), transaction.transaction_code)
    
    return TransactionResponse(
        id=str(transaction.id),
        transaction_code=transaction.transaction_code,
        amount=int(transaction.amount),
        status=transaction.status,
        qr_url=qr_url,
        bank_name=SEPAY_BANK_NAME,
        account_number=SEPAY_ACCOUNT_NUMBER,
        account_name=SEPAY_ACCOUNT_NAME,
        transfer_content=transaction.transaction_code,
        expires_at=transaction.expires_at,
        created_at=transaction.created_at
    )


# ============================================================
# TEST ENDPOINT (Remove in production!)
# ============================================================

@router.post(
    "/test-complete/{transaction_code}",
    summary="[TEST] Giả lập thanh toán thành công",
    tags=["Test"]
)
async def test_complete_transaction(
    transaction_code: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    TEST ONLY - Simulate successful payment.
    This endpoint should be removed in production!
    """
    
    # Find pending transaction
    result = await session.execute(
        text("""
            SELECT id, user_id, amount
            FROM transactions
            WHERE transaction_code = :code
            AND user_id = :user_id
            AND status = 'pending'
        """),
        {"code": transaction_code, "user_id": str(user.id)}
    )
    transaction = result.fetchone()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy giao dịch pending"
        )
    
    # Update transaction to completed
    await session.execute(
        text("""
            UPDATE transactions
            SET status = 'completed',
                completed_at = NOW(),
                updated_at = NOW(),
                note = 'Completed via test endpoint'
            WHERE id = :id
        """),
        {"id": str(transaction.id)}
    )
    
    # Update user balance
    await session.execute(
        text("""
            UPDATE users
            SET balance = COALESCE(balance, 0) + :amount
            WHERE id = :user_id
        """),
        {
            "amount": transaction.amount,
            "user_id": str(transaction.user_id)
        }
    )
    
    await session.commit()
    
    return {
        "status": "success",
        "message": f"Đã cộng {transaction.amount:,.0f} VNĐ vào tài khoản",
        "transaction_code": transaction_code
    }
