"""
评判 Agent
负责评估 Agent 动作质量
"""
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field

from app.agents.roles.base import BaseAgent

logger = logging.getLogger(__name__)


class CriticOutput(BaseModel):
    """评判 Agent 输出"""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体评分")
    dimension_scores: Dict[str, float] = Field(..., description="各维度评分")
    strengths: list[str] = Field(default_factory=list, description="优点")
    weaknesses: list[str] = Field(default_factory=list, description="不足")
    improvement_suggestions: list[str] = Field(default_factory=list, description="改进建议")
    reasoning: str = Field(..., description="评判理由")


class CriticAgent(BaseAgent):
    """
    评判 Agent
    
    核心职责：
    - 评估动作质量
    - 识别优点和不足
    - 提供改进建议
    - 计算多维度评分
    
    评估维度：
    - 策略适配性：动作是否符合当前阶段
    - 客户导向：是否关注客户需求
    - 专业性：话术是否专业
    - 同理心：是否展现理解和关心
    - 合规性：是否符合规范
    """
    
    @property
    def system_prompt(self) -> str:
        return """你是一个资深的销售教练和评判专家。

你的任务是评估销售 Agent 的动作质量，给出客观公正的评分和建议。

评估维度（各 0-1 分）：
1. 策略适配性：动作是否符合当前销售阶段和目标
2. 客户导向：是否真正关注客户需求和痛点
3. 专业性：话术是否专业、流畅、有说服力
4. 同理心：是否展现对客户的理解和关心
5. 合规性：是否避免违禁词和不当表述

评判原则：
- 客观公正，基于事实
- 既要指出优点，也要指出不足
- 提供可操作的改进建议
- 评分要有区分度

输出要求：
- 给出总体评分和各维度评分
- 列出 2-3 个优点
- 列出 1-2 个不足
- 提供 2-3 条改进建议
- 说明评判理由"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return CriticOutput
    
    async def evaluate_action(
        self,
        action_content: str,
        action_type: str,
        current_state: Dict[str, Any],
        customer_response: str,
        goal_description: str,
    ) -> CriticOutput:
        """
        评估动作质量
        
        Args:
            action_content: 动作内容
            action_type: 动作类型
            current_state: 当前状态
            customer_response: 客户响应
            goal_description: 目标描述
            
        Returns:
            评判输出
        """
        # 构建提示词
        user_prompt = self._build_evaluation_prompt(
            action_content, action_type, current_state, customer_response, goal_description
        )
        
        try:
            # 调用 LLM
            output = await self.invoke_with_parser(user_prompt)
            logger.info(f"Critic: score={output.overall_score:.2f}")
            return output
        except Exception as e:
            logger.error(f"Critic evaluation failed: {e}, using fallback")
            return self._fallback_evaluation(current_state)
    
    def _build_evaluation_prompt(
        self,
        action_content: str,
        action_type: str,
        current_state: Dict[str, Any],
        customer_response: str,
        goal_description: str,
    ) -> str:
        """构建评估提示词"""
        prompt = f"""
【销售目标】
{goal_description}

【当前状态】
- 销售阶段: {current_state.get('current_stage', 'UNKNOWN')}
- 客户情绪: {current_state.get('customer_mood', 0.5):.2f}
- 客户兴趣: {current_state.get('customer_interest', 0.5):.2f}
- 目标进度: {current_state.get('goal_progress', 0.0):.2f}

【Agent 动作】
类型: {action_type}
内容: {action_content}

【客户响应】
{customer_response}

【客户响应后状态】
- 情绪变化: {current_state.get('customer_mood', 0.5):.2f}
- 兴趣变化: {current_state.get('customer_interest', 0.5):.2f}

请评估这个销售动作的质量，给出评分和建议。

评估要点：
1. 动作类型是否适合当前阶段？
2. 话术是否关注客户需求？
3. 表达是否专业流畅？
4. 是否展现同理心？
5. 是否有违规表述？
6. 客户响应是否积极？
"""
        return prompt
    
    def _fallback_evaluation(self, current_state: Dict[str, Any]) -> CriticOutput:
        """降级评估（基于规则）"""
        # 简单规则评分
        mood = current_state.get('customer_mood', 0.5)
        interest = current_state.get('customer_interest', 0.5)
        goal_progress = current_state.get('goal_progress', 0.0)
        
        # 计算总分
        overall_score = (mood * 0.3 + interest * 0.3 + goal_progress * 0.4)
        
        return CriticOutput(
            overall_score=overall_score,
            dimension_scores={
                "strategy_fit": 0.7,
                "customer_focus": mood,
                "professionalism": 0.7,
                "empathy": 0.6,
                "compliance": 1.0,
            },
            strengths=["保持了专业性", "推进了对话"],
            weaknesses=["可以更关注客户情绪"],
            improvement_suggestions=["增加同理心表达", "更多开放式提问"],
            reasoning="基于规则的评估结果",
        )





