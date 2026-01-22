"""
Adoption Tracker V3 - 采纳归因器
封装现有 adoption tracker，输出 AdoptionLog
追踪建议→采纳→skill_delta
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.v3_agent_outputs import AdoptionLog
from app.schemas.v3_agent_outputs import CoachAdvice, Evaluation
from app.services.adoption_tracker import AdoptionTracker
from app.services.model_gateway import ModelGateway, BudgetManager

logger = logging.getLogger(__name__)


class AdoptionTrackerV3:
    """Adoption Tracker V3 - 采纳归因器"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        # 封装现有 Adoption Tracker
        self.adoption_tracker = AdoptionTracker()
    
    async def track(
        self,
        session_id: str,
        user_id: str,
        turn_number: int,
        coach_advice: Optional[CoachAdvice],
        evaluation: Optional[Evaluation],
        db: AsyncSession,
    ) -> Optional[AdoptionLog]:
        """
        追踪采纳
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            turn_number: 轮次号
            coach_advice: 教练建议（可选）
            evaluation: 评估结果（可选）
            db: 数据库会话
            
        Returns:
            AdoptionLog（如果检测到采纳）
        """
        if not coach_advice:
            return None
        
        # 注册建议（如果之前未注册）
        # 注意：这里简化处理，实际需要从历史中查找前1-2轮的建议
        suggestion_id = self.adoption_tracker.register_suggestion(
            session_id=session_id,
            turn_id=turn_number - 1,  # 假设是上一轮的建议
            coach_output=None,  # 需要转换，这里简化
            baseline_scores={},
            stage="",
        )
        
        # 分析采纳（调用现有 Adoption Tracker）
        adoption_analysis = await self.adoption_tracker.analyze_adoption(
            session_id=session_id,
            user_id=user_id,
            current_turn=turn_number,
            user_message="",  # 需要从历史获取
            npc_response="",  # 需要从历史获取
            db=db,
        )
        
        if not adoption_analysis:
            return None
        
        # 转换为 AdoptionLog
        return AdoptionLog(
            suggestion_id=suggestion_id,
            suggestion_text=coach_advice.suggested_reply,
            was_adopted=adoption_analysis.adopted,
            adoption_evidence=adoption_analysis.adoption_evidence,
            adoption_style=adoption_analysis.adoption_style.value if hasattr(adoption_analysis.adoption_style, 'value') else str(adoption_analysis.adoption_style),
            is_effective=adoption_analysis.is_effective,
            skill_delta=adoption_analysis.skill_delta,
            feedback_signal=adoption_analysis.feedback_signal,
            turn_number=turn_number,
            timestamp=adoption_analysis.timestamp.isoformat() if hasattr(adoption_analysis.timestamp, 'isoformat') else str(adoption_analysis.timestamp),
        )
