from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from modules.coins.domain.ports.coins_repository import CoinsRepositoryPort
from modules.coins.domain.ports.mission_repository import MissionRepositoryPort
from modules.coins.domain.entities.transaction import UserCoins, CoinTransaction
from modules.coins.domain.entities.mission import Mission, UserMission
from modules.coins.infrastructure.models import (
    UserCoinsModel, 
    CoinTransactionModel, 
    MissionModel, 
    UserMissionModel
)

class SQLAlchemyCoinsRepository(CoinsRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_coins(self, user_id: UUID) -> Optional[UserCoins]:
        result = await self.session.execute(
            select(UserCoinsModel).where(UserCoinsModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return UserCoins(
            user_id=model.user_id,
            current_coins=model.current_coins,
            lifetime_earned=model.lifetime_earned,
            lifetime_spent=model.lifetime_spent,
            last_refresh_date=model.last_refresh_date,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    async def update_user_coins(self, user_coins: UserCoins) -> UserCoins:
        result = await self.session.execute(
            select(UserCoinsModel).where(UserCoinsModel.user_id == user_coins.user_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            model = UserCoinsModel(user_id=user_coins.user_id)
            self.session.add(model)
        
        model.current_coins = user_coins.current_coins
        model.lifetime_earned = user_coins.lifetime_earned
        model.lifetime_spent = user_coins.lifetime_spent
        model.last_refresh_date = user_coins.last_refresh_date
        model.updated_at = user_coins.updated_at
        
        # Commits are handled by the caller/dependency lifecycle in this project
        return user_coins

    async def create_transaction(self, transaction: CoinTransaction) -> CoinTransaction:
        model = CoinTransactionModel(
            user_id=transaction.user_id,
            amount=transaction.amount,
            balance_after=transaction.balance_after,
            transaction_type=transaction.transaction_type,
            service_type=transaction.service_type,
            reference_id=transaction.reference_id,
            description=transaction.description
        )
        self.session.add(model)
        await self.session.flush() # To get the auto-generated ID/timestamp
        transaction.id = model.id
        transaction.created_at = model.created_at
        return transaction

    async def get_transactions_by_user(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[CoinTransaction]:
        result = await self.session.execute(
            select(CoinTransactionModel)
            .where(CoinTransactionModel.user_id == user_id)
            .order_by(desc(CoinTransactionModel.created_at))
            .limit(limit).offset(offset)
        )
        models = result.scalars().all()
        
        return [
            CoinTransaction(
                id=m.id,
                user_id=m.user_id,
                amount=m.amount,
                balance_after=m.balance_after,
                transaction_type=m.transaction_type,
                service_type=m.service_type,
                reference_id=m.reference_id,
                description=m.description,
                created_at=m.created_at
            ) for m in models
        ]


class SQLAlchemyMissionRepository(MissionRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_mission(self, mission_id: UUID) -> Optional[Mission]:
        result = await self.session.execute(
            select(MissionModel).where(MissionModel.id == mission_id)
        )
        m = result.scalar_one_or_none()
        if not m: return None
        return Mission(
            id=m.id, name=m.name, description=m.description, mission_type=m.mission_type,
            coin_reward=m.coin_reward, is_repeatable=m.is_repeatable,
            repeat_frequency=m.repeat_frequency, max_per_period=m.max_per_period,
            requirements=m.requirements, is_active=m.is_active, icon=m.icon, created_at=m.created_at
        )

    async def get_active_missions(self) -> List[Mission]:
        result = await self.session.execute(
            select(MissionModel).where(MissionModel.is_active == True)
        )
        models = result.scalars().all()
        return [Mission(
            id=m.id, name=m.name, description=m.description, mission_type=m.mission_type,
            coin_reward=m.coin_reward, is_repeatable=m.is_repeatable,
            repeat_frequency=m.repeat_frequency, max_per_period=m.max_per_period,
            requirements=m.requirements, is_active=m.is_active, icon=m.icon, created_at=m.created_at
        ) for m in models]

    async def get_user_mission(self, user_id: UUID, mission_id: UUID) -> Optional[UserMission]:
        result = await self.session.execute(
            select(UserMissionModel).where(
                UserMissionModel.user_id == user_id,
                UserMissionModel.mission_id == mission_id
            )
        )
        m = result.scalar_one_or_none()
        if not m: return None
        return UserMission(
            id=m.id, user_id=m.user_id, mission_id=m.mission_id,
            status=m.status, progress=m.progress, completed_at=m.completed_at,
            coins_earned=m.coins_earned, created_at=m.created_at
        )

    async def get_user_missions(self, user_id: UUID) -> List[UserMission]:
        result = await self.session.execute(
            select(UserMissionModel).where(UserMissionModel.user_id == user_id)
        )
        models = result.scalars().all()
        return [UserMission(
            id=m.id, user_id=m.user_id, mission_id=m.mission_id,
            status=m.status, progress=m.progress, completed_at=m.completed_at,
            coins_earned=m.coins_earned, created_at=m.created_at
        ) for m in models]

    async def update_user_mission(self, user_mission: UserMission) -> UserMission:
        result = await self.session.execute(
            select(UserMissionModel).where(UserMissionModel.id == user_mission.id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.status = user_mission.status
            model.progress = user_mission.progress
            model.completed_at = user_mission.completed_at
            model.coins_earned = user_mission.coins_earned
            self.session.add(model)
            await self.session.flush()
        return user_mission

    async def create_user_mission(self, user_mission: UserMission) -> UserMission:
        model = UserMissionModel(
            id=user_mission.id,
            user_id=user_mission.user_id,
            mission_id=user_mission.mission_id,
            status=user_mission.status,
            progress=user_mission.progress,
            completed_at=user_mission.completed_at,
            coins_earned=user_mission.coins_earned
        )
        self.session.add(model)
        await self.session.flush()
        return user_mission
