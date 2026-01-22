"""
Micro Feedback Service - MVP 轻量复盘服务
生成<=3条可执行反馈，不打分、不排名、不画雷达图
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.mvp import MicroFeedbackItem, MicroFeedbackResponse
from app.models.runtime_models import Session, Message
from app.schemas.agent_outputs import EvaluatorOutput

logger = logging.getLogger(__name__)


class MicroFeedbackService:
    """
    轻量复盘服务
    
    核心职责：
    - 生成<=3条可执行反馈
    - 每条反馈包含可直接复用的话术
    - 规则优先，避免长篇报告
    """
    
    async def generate_feedback(
        self,
        session_id: str,
        db: AsyncSession,
    ) -> MicroFeedbackResponse:
        """
        生成轻量复盘反馈
        
        Args:
            session_id: 会话ID
            db: 数据库会话
            
        Returns:
            轻量复盘响应（<=3条）
        """
        # 加载会话和消息
        session_result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            return MicroFeedbackResponse(
                feedback_items=[],
                session_id=session_id,
                total_turns=0,
            )
        
        # 加载所有消息
        messages_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_number)
        )
        messages = messages_result.scalars().all()
        
        feedback_items = []
        
        # 规则1：检查是否出现异议但未推进
        objection_found = False
        closing_attempted = False
        
        for msg in messages:
            if msg.role == "user":
                content = msg.content.lower()
                # 检测异议
                if any(word in content for word in ["贵", "价格", "考虑", "担心", "不需要"]):
                    objection_found = True
                # 检测推进尝试
                if any(word in content for word in ["办", "申请", "开通", "确定"]):
                    closing_attempted = True
        
        if objection_found and not closing_attempted:
            feedback_items.append(MicroFeedbackItem(
                title="异议处理后可推进",
                what_happened="您识别了客户的异议，但没有及时推进成交",
                better_move="在化解异议后，可以尝试推进：'既然您已经了解了权益，不如现在就办理，还能享受当前优惠'",
                copyable_phrase="既然您已经了解了权益，不如现在就办理，还能享受当前优惠",
            ))
        
        # 规则2：检查是否出现推进信号但未给下一步
        closing_signals = ["好", "可以", "行", "同意", "确定"]
        closing_signal_found = False
        next_step_given = False
        
        for msg in messages:
            if msg.role == "npc":
                content = msg.content.lower()
                if any(signal in content for signal in closing_signals):
                    closing_signal_found = True
                    # 检查下一条用户消息是否给出下一步
                    for next_msg in messages:
                        if next_msg.turn_number > msg.turn_number and next_msg.role == "user":
                            if any(word in next_msg.content for word in ["办理", "申请", "提交", "下一步"]):
                                next_step_given = True
                            break
        
        if closing_signal_found and not next_step_given:
            feedback_items.append(MicroFeedbackItem(
                title="抓住推进时机",
                what_happened="客户表达了积极信号，但您没有及时给出明确的下一步",
                better_move="当客户表示同意时，立即给出具体行动：'太好了！我现在就帮您提交申请，请确认一下您的信息'",
                copyable_phrase="太好了！我现在就帮您提交申请，请确认一下您的信息",
            ))
        
        # 规则3：检查是否出现高风险表达
        high_risk_found = False
        for msg in messages:
            if msg.role == "user" and msg.compliance_result:
                compliance = msg.compliance_result
                if isinstance(compliance, dict):
                    if compliance.get("blocked") or compliance.get("risk_level") == "BLOCK":
                        high_risk_found = True
                        break
        
        if high_risk_found:
            feedback_items.append(MicroFeedbackItem(
                title="避免高风险表达",
                what_happened="您的表达中存在合规风险，可能影响客户信任",
                better_move="使用更安全的表述：'根据过往经验，大多数情况下可以满足您的需求'，避免使用绝对化承诺",
                copyable_phrase="根据过往经验，大多数情况下可以满足您的需求",
            ))
        
        # 如果反馈不足3条，添加通用反馈
        if len(feedback_items) < 3:
            # 检查是否缺少权益介绍
            benefit_mentioned = False
            for msg in messages:
                if msg.role == "user":
                    if any(word in msg.content for word in ["权益", "优惠", "积分", "年费"]):
                        benefit_mentioned = True
                        break
            
            if not benefit_mentioned and len(feedback_items) < 3:
                feedback_items.append(MicroFeedbackItem(
                    title="主动介绍核心权益",
                    what_happened="对话中较少提及核心权益，可能错失吸引客户的机会",
                    better_move="在适当时机主动介绍：'这张卡最大的亮点是机场贵宾厅和酒店升级权益，特别适合经常出差的您'",
                    copyable_phrase="这张卡最大的亮点是机场贵宾厅和酒店升级权益，特别适合经常出差的您",
                ))
        
        # 确保不超过3条
        feedback_items = feedback_items[:3]
        
        logger.info(f"Generated {len(feedback_items)} feedback items for session {session_id}")
        
        return MicroFeedbackResponse(
            feedback_items=feedback_items,
            session_id=session_id,
            total_turns=session.total_turns,
        )

