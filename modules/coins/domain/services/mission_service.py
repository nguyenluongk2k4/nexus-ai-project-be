from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any
from datetime import datetime
from modules.coins.domain.ports.mission_repository import MissionRepositoryPort
from modules.coins.domain.services.coins_service import CoinsService
from modules.coins.domain.entities.mission import UserMission

class MissionService:
    def __init__(self, repository: MissionRepositoryPort, coins_service: CoinsService):
        self.repository = repository
        self.coins_service = coins_service

    async def get_available_missions(self) -> List[Any]:
        return await self.repository.get_active_missions()

    async def get_user_progress(self, user_id: UUID) -> List[UserMission]:
        return await self.repository.get_user_missions(user_id)

    async def update_progress(self, user_id: UUID, mission_type: str, progress_data: Dict[str, Any]):
        active_missions = await self.repository.get_active_missions()
        relevant_missions = [m for m in active_missions if m.mission_type == mission_type]
        
        for mission in relevant_missions:
            user_mission = await self.repository.get_user_mission(user_id, mission.id)
            
            if not user_mission:
                user_mission = UserMission(
                    id=uuid4(),
                    user_id=user_id,
                    mission_id=mission.id,
                    status='in_progress',
                    progress={}
                )
                await self.repository.create_user_mission(user_mission)
            
            if user_mission.status == 'completed' and not mission.is_repeatable:
                continue
                
            # Logic to update progress
            current_progress = user_mission.progress or {}
            
            # If progress_data has 'increment', we add it to the current count
            if 'increment' in progress_data:
                field = progress_data.get('field', 'count')
                current_value = current_progress.get(field, 0)
                new_value = current_value + progress_data['increment']
                current_progress[field] = new_value
                
                # Update visual progress string
                required = mission.requirements.get('count', 1)
                if new_value >= required:
                    current_progress['progress'] = 'completed'
                else:
                    current_progress['progress'] = f"{new_value}/{required}"
            else:
                # Otherwise, merge the new data
                current_progress.update(progress_data)
                if 'completed' in progress_data and progress_data['completed']:
                    current_progress['progress'] = 'completed'
                
            user_mission.progress = current_progress
            
            # Check for completion
            is_completed = self._check_completion(mission, current_progress)
            
            if is_completed:
                # Instead of 'completed', set to 'not_get_point' to allow manual claiming
                user_mission.status = 'not_get_point'
                user_mission.completed_at = datetime.now()
                # Ensure progress is set to 'completed'
                user_mission.progress['progress'] = 'completed'
            
            await self.repository.update_user_mission(user_mission)

    async def claim_reward(self, user_id: UUID, mission_id: UUID) -> UserMission:
        """Manually claim reward for a completed mission"""
        user_mission = await self.repository.get_user_mission(user_id, mission_id)
        if not user_mission:
            raise ValueError("Mission not started or not found")
            
        if user_mission.status != 'not_get_point':
            if user_mission.status == 'completed':
                raise ValueError("Reward already claimed")
            raise ValueError("Mission not completed yet")
            
        mission = await self.repository.get_mission(mission_id)
        if not mission:
            raise ValueError("Mission configuration not found")
            
        # Update status and award coins
        user_mission.status = 'completed'
        user_mission.coins_earned = mission.coin_reward
        # Update progress to the "claimed" state
        user_mission.progress = {"completed": True}
        
        await self.coins_service.award_coins(
            user_id=user_id,
            amount=mission.coin_reward,
            transaction_type='mission',
            reference_id=mission.id,
            description=f"Claimed reward for mission: {mission.name}"
        )
        
        return await self.repository.update_user_mission(user_mission)

    def _check_completion(self, mission: Any, progress: Dict[str, Any]) -> bool:
        if not mission.requirements:
            return True
            
        # Example logic for count-based missions
        if 'count' in mission.requirements:
            required_count = mission.requirements['count']
            current_count = progress.get('count', 0)
            return current_count >= required_count
            
        # Example logic for boolean missions (e.g. update_profile)
        if 'completed' in mission.requirements:
            return progress.get('completed') is True
            
        return False
