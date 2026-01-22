"""
规划 Agent
负责高层策略规划和动作选择
"""
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.sales_simulation.schemas.trajectory import ActionType

logger = logging.getLogger(__name__)


class PlannerOutput(BaseModel):
    """规划 Agent 输出"""
    action_type: str = Field(..., description="推荐的动作类型")
    reasoning: str = Field(..., description="推理过程")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    alternative_actions: list[str] = Field(default_factory=list, description="备选动作")


class PlannerAgent(BaseAgent):
    """
    规划 Agent
    
    核心职责：
    - 分析当前状态
    - 制定高层策略
    - 选择下一步动作类型
    - 评估动作置信度
    
    复用 BaseAgent 的 LLM 调用能力
    """
    
    @property
    def system_prompt(self) -> str:
        return """你是一个专业的销售策略规划专家。

你的任务是分析当前销售场景状态，制定最优的下一步动作策略。

核心原则：
1. 目标导向：始终以达成销售目标为核心
2. 客户中心：关注客户情绪、兴趣和需求
3. 阶段适配：根据销售阶段选择合适的动作
4. 风险控制：避免过早促单或过度推销

可选动作类型：
- speak: 一般性陈述
- listen: 倾听客户
- question: 提问挖掘
- present: 产品展示
- handle_objection: 处理异议
- close: 促单成交
- end: 结束对话

输出要求：
- 选择最合适的动作类型
- 说明推理过程
- 给出置信度评分
- 提供备选方案"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return PlannerOutput
    
    async def plan_next_action(
        self,
        current_state: Dict[str, Any],
        conversation_history: list[Dict[str, Any]],
        goal_description: str,
    ) -> PlannerOutput:
        """
        规划下一步动作
        
        Args:
            current_state: 当前状态
            conversation_history: 对话历史
            goal_description: 目标描述
            
        Returns:
            规划输出
        """
        # 构建提示词
        user_prompt = self._build_planning_prompt(
            current_state, conversation_history, goal_description
        )
        
        try:
            # 调用 LLM
            output = await self.invoke_with_parser(user_prompt)
            logger.info(f"Planner: {output.action_type} (confidence: {output.confidence:.2f})")
            return output
        except Exception as e:
            logger.error(f"Planner failed: {e}, using fallback")
            return self._fallback_plan(current_state)
    
    def _build_planning_prompt(
        self,
        current_state: Dict[str, Any],
        conversation_history: list[Dict[str, Any]],
        goal_description: str,
    ) -> str:
        """构建规划提示词"""
        # 格式化对话历史
        history_text = "\n".join([
            f"轮次{h['step']}: Agent: {h['agent']}\n客户: {h['customer']}"
            for h in conversation_history[-3:]  # 最近3轮
        ])
        
        prompt = f"""
【销售目标】
{goal_description}

【当前状态】
- 销售阶段: {current_state.get('current_stage', 'UNKNOWN')}
- 客户情绪: {current_state.get('customer_mood', 0.5):.2f}
- 客户兴趣: {current_state.get('customer_interest', 0.5):.2f}
- 客户信任: {current_state.get('customer_trust', 0.5):.2f}
- 目标进度: {current_state.get('goal_progress', 0.0):.2f}
- 已对话轮数: {current_state.get('conversation_turns', 0)}

【最近对话】
{history_text if history_text else "（尚未开始对话）"}

【检测到的信号】
{', '.join(current_state.get('detected_signals', [])) or "无"}

请分析当前情况，规划最优的下一步动作。
"""
        return prompt
    
    def _fallback_plan(self, current_state: Dict[str, Any]) -> PlannerOutput:
        """降级规划（基于规则）"""
        stage = current_state.get('current_stage', 'OPENING')
        goal_progress = current_state.get('goal_progress', 0.0)
        
        # 简单规则
        if stage == 'OPENING':
            action_type = "question"
            reasoning = "开场阶段，应该通过提问建立联系"
        elif stage == 'NEEDS_DISCOVERY':
            action_type = "question"
            reasoning = "需求挖掘阶段，应该深入提问"
        elif stage == 'PRODUCT_INTRO':
            action_type = "present"
            reasoning = "产品介绍阶段，应该展示价值"
        elif goal_progress > 0.8:
            action_type = "close"
            reasoning = "目标接近达成，可以尝试促单"
        else:
            action_type = "speak"
            reasoning = "继续推进对话"
        
        return PlannerOutput(
            action_type=action_type,
            reasoning=reasoning,
            confidence=0.6,
            alternative_actions=["speak", "question"],
        )





