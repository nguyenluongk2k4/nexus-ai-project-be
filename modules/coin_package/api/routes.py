from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.domain.entities import User
from modules.user.api.deps import require_admin
from shared.database.connection import get_db

from .schemas import CoinPackageCreateRequest, CoinPackageResponse


router = APIRouter(prefix="/coin-packages", tags=["Coin Package"])


@router.post("", response_model=CoinPackageResponse, status_code=status.HTTP_201_CREATED)
async def create_coin_package(
    request: CoinPackageCreateRequest,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = await session.execute(
        text("SELECT id FROM coin_packages WHERE id = :id"),
        {"id": request.id},
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Package id already exists")

    created = await session.execute(
        text(
            """
            INSERT INTO coin_packages (
                id, name, price, coin_amount, bonus_amount,
                badge_color, is_popular, is_active, display_order
            )
            VALUES (
                :id, :name, :price, :coin_amount, :bonus_amount,
                :badge_color, :is_popular, TRUE, :display_order
            )
            RETURNING id, name, price, coin_amount, bonus_amount,
                      badge_color, is_popular, is_active, display_order,
                      created_at, updated_at
            """
        ),
        {
            "id": request.id,
            "name": request.name,
            "price": request.price,
            "coin_amount": request.coin_amount,
            "bonus_amount": request.bonus_amount,
            "badge_color": request.badge_color,
            "is_popular": request.is_popular,
            "display_order": request.display_order,
        },
    )
    await session.commit()

    row = created.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Cannot create coin package")

    return CoinPackageResponse(
        id=row.id,
        name=row.name,
        price=float(row.price),
        coin_amount=row.coin_amount,
        bonus_amount=row.bonus_amount or 0,
        badge_color=row.badge_color or "#8B5CF6",
        is_popular=row.is_popular or False,
        is_active=row.is_active,
        display_order=row.display_order or 0,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=List[CoinPackageResponse])
async def get_coin_packages(
    include_inactive: bool = Query(False, description="Bao gom cac goi da an"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = """
        SELECT id, name, price, coin_amount, bonus_amount,
               badge_color, is_popular, is_active, display_order,
               created_at, updated_at
        FROM coin_packages
    """

    if not include_inactive:
        query += " WHERE is_active = TRUE"

    query += " ORDER BY display_order ASC, created_at DESC"

    result = await session.execute(text(query))
    rows = result.fetchall()

    return [
        CoinPackageResponse(
            id=row.id,
            name=row.name,
            price=float(row.price),
            coin_amount=row.coin_amount,
            bonus_amount=row.bonus_amount or 0,
            badge_color=row.badge_color or "#8B5CF6",
            is_popular=row.is_popular or False,
            is_active=row.is_active,
            display_order=row.display_order or 0,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/{package_id}", response_model=CoinPackageResponse)
async def get_coin_package_detail(
    package_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await session.execute(
        text(
            """
            SELECT id, name, price, coin_amount, bonus_amount,
                   badge_color, is_popular, is_active, display_order,
                   created_at, updated_at
            FROM coin_packages
            WHERE id = :package_id
            """
        ),
        {"package_id": package_id},
    )

    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Coin package not found")

    return CoinPackageResponse(
        id=row.id,
        name=row.name,
        price=float(row.price),
        coin_amount=row.coin_amount,
        bonus_amount=row.bonus_amount or 0,
        badge_color=row.badge_color or "#8B5CF6",
        is_popular=row.is_popular or False,
        is_active=row.is_active,
        display_order=row.display_order or 0,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/{package_id}", response_model=dict)
async def delete_coin_package(
    package_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await session.execute(
        text("SELECT id, is_active FROM coin_packages WHERE id = :package_id"),
        {"package_id": package_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Coin package not found")

    if row.is_active is False:
        return {"success": True, "message": "Package already inactive"}

    await session.execute(
        text(
            """
            UPDATE coin_packages
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = :package_id
            """
        ),
        {"package_id": package_id},
    )
    await session.commit()

    return {"success": True, "message": "Package deleted (soft delete)"}
