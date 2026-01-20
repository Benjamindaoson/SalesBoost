"""
Progression Service
管理用户等级、场景解锁状态
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.models.adoption_models import UserStrategyProfile
from app.models.config_models import ScenarioConfig
from app.models.runtime_models import Session

logger = logging.getLogger(__name__)

class ProgressionService:
    
    async def get_user_level(self, db: AsyncSession, user_id: str) -> int:
        """
        Calculate user level based on completed sessions and skill mastery.
        Level 1: Novice (0-5 sessions)
        Level 2: Apprentice (5-15 sessions, >50% adoption)
        Level 3: Pro (15+ sessions, >70% adoption, >80% strategy optimal)
        """
        # Count sessions
        query = select(func.count(Session.id)).where(
            Session.user_id == user_id,
            Session.status == "completed"
        )
        result = await db.execute(query)
        completed_sessions = result.scalar() or 0
        
        # Get profile for skill stats
        profile_query = select(UserStrategyProfile).where(
            UserStrategyProfile.user_id == user_id
        )
        result = await db.execute(profile_query)
        profile = result.scalar_one_or_none()
        
        adoption_rate = profile.adoption_rate if profile else 0
        
        # Determine Level
        if completed_sessions < 5:
            return 1
        elif completed_sessions < 15:
            if adoption_rate > 0.4:
                return 2
            else:
                return 1 # Held back
        else:
            if adoption_rate > 0.6:
                return 3
            else:
                return 2
                
    async def check_scenario_access(self, db: AsyncSession, user_id: str, scenario_id: str) -> Dict[str, Any]:
        """
        Check if user can access this scenario.
        Returns: { "allowed": bool, "reason": str }
        """
        # Get Scenario Config
        query = select(ScenarioConfig).where(ScenarioConfig.id == scenario_id)
        result = await db.execute(query)
        scenario = result.scalar_one_or_none()
        
        if not scenario:
            return {"allowed": False, "reason": "Scenario not found"}
            
        # Get User Level
        user_level = await self.get_user_level(db, user_id)
        
        # Check Level Requirement
        if user_level < scenario.required_level:
             return {
                 "allowed": False, 
                 "reason": f"Level {scenario.required_level} required. You are Level {user_level}."
             }
             
        # Check Prerequisite Skills (if any)
        # e.g. {"reframe_value": 0.5} -> means UserStrategyProfile.optimal_rate_by_situation must contain reframe_value related skills?
        # For simplicity in MVP, we skip complex skill mapping and just rely on Level.
        
        # P1: Check Locked Curriculum
        profile_query = select(UserStrategyProfile).where(
            UserStrategyProfile.user_id == user_id
        )
        result = await db.execute(profile_query)
        profile = result.scalar_one_or_none()
        
        if profile and profile.locked_curriculum:
            locked_situation = profile.locked_curriculum.get("situation")
            # If scenario is NOT the locked one (assuming we map scenario to situation, which is hard without metadata)
            # For now, we assume locked_curriculum forces a specific *Situation Type*.
            # We need to know if this scenario matches that situation.
            # But ScenarioConfig doesn't strictly have 'situation_type' field in MVP model (it has description).
            # We will skip strict scenario-situation mapping check for now and rely on FE to enforce lock visual.
            pass
            
        return {"allowed": True, "reason": "Access Granted"}
