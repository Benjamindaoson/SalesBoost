"""
对话 Agent
负责生成具体的对话内容
"""
import logging
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field

from app.agents.roles.base import BaseAgent
from app.sales_simulation.schemas.trajectory import ActionType

logger = logging.getLogger(__name__)


class DialogueOutput(BaseModel):
    """对话 Agent 输出"""
    content: str = Field(..., description="对话内容")
    tone: str = Field(default="professional", description="语气：professional/friendly/empathetic")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")


class DialogueAgent(BaseAgent):
    """
    对话 Agent
    
    核心职责：
    - 根据动作类型生成具体话术
    - 保持对话自然流畅
    - 适应客户情绪和状态
    - 遵循销售最佳实践
    
    复用 BaseAgent 的 LLM 调用能力
    """
    
    @property
    def system_prompt(self) -> str:
        return """你是一个专业的销售对话专家。

你的任务是根据策略规划，生成具体的销售话术。

核心原则：
1. 自然流畅：对话要自然，避免生硬
2. 同理心：展现对客户的理解和关心
3. 价值导向：聚焦客户价值，而非产品功能
4. 专业性：保持专业但不失亲和力
5. 合规性：避免使用"保证"、"一定"、"绝对"等违禁词

话术要求：
- 简洁明了，一次表达一个核心观点
- 使用开放式提问引导客户
- 适应客户当前情绪状态
- 体现专业销售技巧

输出格式：
- 直接输出话术内容
- 说明语气风格
- 给出置信度"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return DialogueOutput
    
    async def generate_dialogue(
        self,
        action_type: str,
        current_state: Dict[str, Any],
        conversation_history: list[Dict[str, Any]],
        customer_profile: Dict[str, Any],
    ) -> DialogueOutput:
        """
        生成对话内容
        
        Args:
            action_type: 动作类型
            current_state: 当前状态
            conversation_history: 对话历史
            customer_profile: 客户画像
            
        Returns:
            对话输出
        """
        # 构建提示词
        user_prompt = self._build_dialogue_prompt(
            action_type, current_state, conversation_history, customer_profile
        )
        
        try:
            # 调用 LLM
            output = await self.invoke_with_parser(user_prompt)
            logger.info(f"Dialogue generated: {output.content[:50]}...")
            return output
        except Exception as e:
            logger.error(f"Dialogue generation failed: {e}, using fallback")
            return self._fallback_dialogue(action_type, current_state)
    
    def _build_dialogue_prompt(
        self,
        action_type: str,
        current_state: Dict[str, Any],
        conversation_history: list[Dict[str, Any]],
        customer_profile: Dict[str, Any],
    ) -> str:
        """构建对话提示词"""
        # 格式化对话历史
        history_text = "\n".join([
            f"轮次{h['step']}: 你: {h['agent']}\n客户: {h['customer']}"
            for h in conversation_history[-3:]
        ])
        
        # 客户最后一句话
        last_customer_message = ""
        if conversation_history:
            last_customer_message = conversation_history[-1].get('customer', '')
        
        prompt = f"""
【动作类型】
{action_type}

【客户画像】
- 姓名: {customer_profile.get('name', '客户')}
- 角色: {customer_profile.get('role', '未知')}
- 决策风格: {customer_profile.get('decision_style', 'analytical')}
- 性格特征: {', '.join(customer_profile.get('personality_traits', []))}

【当前状态】
- 客户情绪: {current_state.get('customer_mood', 0.5):.2f} (0-1)
- 客户兴趣: {current_state.get('customer_interest', 0.5):.2f} (0-1)
- 销售阶段: {current_state.get('current_stage', 'OPENING')}

【最近对话】
{history_text if history_text else "（首次对话）"}

【客户最后说】
{last_customer_message if last_customer_message else "（等待你开场）"}

请根据以上信息，生成一句合适的销售话术。
注意：
1. 避免使用"保证"、"一定"、"绝对"等违禁词
2. 根据客户情绪调整语气
3. 保持对话自然流畅
"""
        return prompt
    
    def _fallback_dialogue(
        self,
        action_type: str,
        current_state: Dict[str, Any],
    ) -> DialogueOutput:
        """降级对话生成（模板）"""
        templates = {
            "question": "请问您目前在这方面遇到的最大挑战是什么？",
            "speak": "我理解您的想法，让我们继续探讨。",
            "present": "让我为您介绍一下我们的解决方案。",
            "handle_objection": "我理解您的顾虑，让我们一起看看如何解决。",
            "close": "基于我们的讨论，您觉得我们可以安排下一步吗？",
            "listen": "请继续说，我在认真听。",
            "end": "感谢您的时间，期待下次交流。",
        }
        
        content = templates.get(action_type, "让我们继续交流。")
        
        return DialogueOutput(
            content=content,
            tone="professional",
            confidence=0.5,
        )





