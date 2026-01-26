"""
Intent Gate Agent
意图识别 / 对齐检测
"""
import logging
from typing import Dict, Any, List, Optional, Type

from app.core.llm_context import LLMCallContext
from pydantic import BaseModel

from app.agents.roles.base import BaseAgent
from app.schemas.agent_outputs import IntentGateOutput, DetectedSlot
from app.schemas.fsm import SalesStage, StageSlotConfig

logger = logging.getLogger(__name__)


class IntentGateAgent(BaseAgent):
    """
    意图门控 Agent
    
    核心职责：
    - 识别用户（销售员）的意图
    - 判断意图是否与当前 FSM 阶段对齐
    - 检测并提取 Slot 填充
    - 如果不对齐，提供引导建议
    """
    
    def __init__(self, **kwargs):
        super().__init__(temperature=0.1, **kwargs)  # 意图识别需要高确定性

    AGENT_TYPE = "intent_gate"
    
    @property
    def system_prompt(self) -> str:
        return """你是 SalesBoost 系统的【意图门控】模块，负责分析销售员的输入。

【你的职责】
1. 识别销售员的意图（想要做什么）
2. 判断这个意图是否与当前销售阶段对齐
3. 从输入中提取可能的 Slot 信息
4. 如果不对齐，给出引导建议

【意图类型】
- greeting: 问候、寒暄
- rapport_building: 建立关系、闲聊
- need_probing: 挖掘需求、提问
- pain_point_discovery: 发现痛点
- product_introduction: 介绍产品
- value_proposition: 传递价值主张
- objection_handling: 处理异议
- closing_attempt: 尝试促单
- follow_up_arrangement: 安排后续
- off_topic: 跑题、无关内容

【阶段对齐规则】
- OPENING: greeting, rapport_building 对齐
- NEEDS_DISCOVERY: need_probing, pain_point_discovery 对齐
- PRODUCT_INTRO: product_introduction, value_proposition 对齐
- OBJECTION_HANDLING: objection_handling 对齐
- CLOSING: closing_attempt, follow_up_arrangement 对齐

【输出要求】
你必须输出严格的 JSON 格式，包含：
- detected_intent: 检测到的意图
- is_aligned: 是否与当前阶段对齐
- alignment_reason: 对齐/不对齐的原因
- detected_slots: 检测到的 Slot 列表
- missing_slots: 当前阶段缺失的 Slot
- suggested_redirect: 如果不对齐，建议的引导话术
- confidence: 置信度
"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return IntentGateOutput
    
    async def analyze(
        self,
        user_message: str,
        current_stage: SalesStage,
        conversation_history: List[Dict[str, Any]],
        stage_config: Optional[StageSlotConfig],
        llm_context: Optional["LLMCallContext"] = None,
    ) -> IntentGateOutput:
        """
        分析用户意图
        
        Args:
            user_message: 用户输入
            current_stage: 当前 FSM 阶段
            conversation_history: 对话历史
            stage_config: 当前阶段配置
            
        Returns:
            意图分析结果
        """
        # 构建对话历史
        history_str = self._format_recent_history(conversation_history)
        
        # 获取当前阶段的 Slot 定义
        slot_definitions = self._format_slot_definitions(stage_config)
        
        user_prompt = f"""【当前销售阶段】
{current_stage.value}

【本阶段需要收集的信息】
{slot_definitions}

【最近对话】
{history_str}

【销售员最新输入】
{user_message}

请分析销售员的意图，判断是否与当前阶段对齐，并提取可能的 Slot 信息。"""
        
        try:
            result = await self.invoke_with_parser(user_prompt, llm_context=llm_context)
            return result
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            # 返回兜底结果
            return IntentGateOutput(
                detected_intent="unknown",
                is_aligned=True,  # 默认对齐，避免阻断流程
                alignment_reason="系统分析异常，默认放行",
                detected_slots=[],
                missing_slots=[],
                suggested_redirect=None,
                confidence=0.5,
            )
    
    def _format_recent_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化最近对话"""
        if not history:
            return "（无历史对话）"
        
        formatted = []
        for msg in history[-4:]:  # 最近 4 条
            role = "销售员" if msg["role"] == "user" else "客户"
            formatted.append(f"{role}：{msg['content']}")
        
        return "\n".join(formatted)
    
    def _format_slot_definitions(self, stage_config: Optional[StageSlotConfig]) -> str:
        """格式化 Slot 定义"""
        if not stage_config:
            return "（无定义）"
        
        formatted = []
        for slot in stage_config.slots:
            required_mark = "【必填】" if slot.required else "【选填】"
            formatted.append(f"- {slot.name} {required_mark}: {slot.description}")
            formatted.append(f"  提取提示：{slot.extraction_hint}")
        
        return "\n".join(formatted)
