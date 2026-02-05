from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from shared.database.connection import get_db
from modules.coins.infrastructure.repository import SQLAlchemyCoinsRepository, SQLAlchemyMissionRepository
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.services.mission_service import MissionService

def get_coins_repository(db: AsyncSession = Depends(get_db)) -> SQLAlchemyCoinsRepository:
    return SQLAlchemyCoinsRepository(db)

def get_mission_repository(db: AsyncSession = Depends(get_db)) -> SQLAlchemyMissionRepository:
    return SQLAlchemyMissionRepository(db)

def get_coins_service(db: AsyncSession = Depends(get_db)) -> CoinsService:
    repo = get_coins_repository(db)
    return CoinsService(repo)

def get_mission_service(db: AsyncSession = Depends(get_db)) -> MissionService:
    repo = get_mission_repository(db)
    coins_service = get_coins_service(db)
    return MissionService(repo, coins_service)
