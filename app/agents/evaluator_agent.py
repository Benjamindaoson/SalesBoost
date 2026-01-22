"""
Evaluator / Judge Agent
五维评分：Integrity, Relevance, Correctness, Logic, Compliance
+ 策略分析：识别用户策略 vs 销冠最优策略
"""
import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import get_db_session_context
from app.models.evaluation_models import EvaluationDimension
from app.agents.base import BaseAgent
from app.schemas.agent_outputs import (
    EvaluatorOutput,
    DimensionScore,
    DetectedSlot,
    ComplianceOutput,
)
from app.schemas.fsm import FSMState, SalesStage, StageSlotConfig
from app.schemas.strategy import StrategyAnalysis
from app.services.strategy_analyzer import StrategyAnalyzer

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseAgent):
    """
    评估 Agent
    
    核心职责：
    - 对销售员的每轮表现进行动态维度评分
    - 判断是否推进了阶段目标
    - 提取本轮填充的 Slot
    - 给出改进建议
    
    评分维度：
    - 从数据库加载配置 (EvaluationDimension)
    - 动态生成 System Prompt
    """

    def __init__(self, **kwargs):
        super().__init__(temperature=0.1, **kwargs)  # 评估需要高确定性
        self.strategy_analyzer = StrategyAnalyzer()
        self._dimensions_cache: List[EvaluationDimension] = []
        self._last_prompt_cache: str = ""

    async def _load_dimensions(self):
        """加载评估维度配置"""
        async with get_db_session_context() as db:
            result = await db.execute(select(EvaluationDimension).where(EvaluationDimension.is_active == True))
            self._dimensions_cache = result.scalars().all()
            
    async def _build_system_prompt(self) -> str:
        """动态构建 System Prompt"""
        if not self._dimensions_cache:
            await self._load_dimensions()
            
        # 如果数据库为空，回退到默认
        if not self._dimensions_cache:
            return self._fallback_system_prompt
            
        dimensions_str = ""
        for dim in self._dimensions_cache:
            criteria = dim.criteria_prompt or "Based on general professional standards."
            dimensions_str += f"{dim.name} (Weight: {dim.weight}):\n{criteria}\n\n"
            
        return f"""You are the **Professional Evaluator** for SalesBoost.

## Scoring Dimensions
Please score based on the following configured dimensions:

{dimensions_str}

## Output Format
Strictly follow the JSON schema provided.
"""

    @property
    def _fallback_system_prompt(self) -> str:
        try:
            with open("app/prompts/evaluator_prompt.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return """You are the SalesBoost Evaluator. Score on: Integrity, Relevance, Correctness, Logic, Compliance."""

    @property
    def system_prompt(self) -> str:
        # Note: This property is sync in BaseAgent, but we need async data loading.
        # Temporary workaround: return cached prompt or fallback
        return self._last_prompt_cache or self._fallback_system_prompt

    @property
    def output_schema(self) -> Type[BaseModel]:
        return EvaluatorOutput
    
    async def evaluate(
        self,
        user_message: str,
        npc_response: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        stage_config: Optional[StageSlotConfig],
        compliance_result: ComplianceOutput,
    ) -> tuple[EvaluatorOutput, Optional[StrategyAnalysis]]:
        """
        评估销售员表现
        
        Args:
            user_message: 销售员输入
            npc_response: NPC 回复
            conversation_history: 对话历史
            fsm_state: 当前 FSM 状态
            stage_config: 当前阶段配置
            compliance_result: 合规检查结果
            
        Returns:
            (评估结果, 策略分析结果)
        """
        # 1. 动态构建 Prompt
        system_prompt = await self._build_system_prompt()
        self._last_prompt_cache = system_prompt
        
        # 获取上一轮 NPC 消息用于情境判断
        prev_npc_message = ""
        for msg in reversed(conversation_history[:-1]):
            if msg.get("role") == "npc":
                prev_npc_message = msg.get("content", "")
                break
        
        # 策略分析
        strategy_analysis = self.strategy_analyzer.analyze_strategy(
            user_message=user_message,
            npc_message=prev_npc_message,
            stage=fsm_state.current_stage,
        )
        
        # 构建对话历史
        history_str = self._format_conversation_history(conversation_history)
        
        # 获取阶段目标和 Slot 定义
        stage_goal = stage_config.goal_description if stage_config else "未知"
        slot_definitions = self._format_slot_definitions(stage_config)
        
        # 合规预判
        compliance_context = self._format_compliance_context(compliance_result)
        
        # 策略分析上下文
        strategy_context = self._format_strategy_context(strategy_analysis)
        
        user_prompt = f"""【当前状态】
- 销售阶段：{fsm_state.current_stage.value}
- 阶段目标：{stage_goal}
- 客户情绪：{fsm_state.npc_mood:.2f}
- 对话轮次：{fsm_state.turn_count}

【本阶段需要收集的信息（Slot）】
{slot_definitions}

【对话历史】
{history_str}

【销售员最新输入】
{user_message}

【客户回复】
{npc_response}

【合规预检结果】
{compliance_context}

【策略分析】
{strategy_context}

请对销售员的这轮表现进行五维评分，判断是否推进了阶段目标，并提取本轮填充的 Slot。"""
        
        try:
            result = await self.invoke_with_parser(user_prompt)
            return result, strategy_analysis
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            # 返回兜底评估
            return self._create_fallback_evaluation(fsm_state, compliance_result), strategy_analysis
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史对话）"
        
        formatted = []
        for msg in history[-6:]:  # 最近 6 条
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
        
        return "\n".join(formatted)
    
    def _format_compliance_context(self, result: ComplianceOutput) -> str:
        """格式化合规上下文"""
        if result.is_compliant:
            return "✅ 合规检查通过，无风险"
        
        risks = []
        for flag in result.risk_flags:
            risks.append(f"⚠️ {flag.risk_type} ({flag.severity}): {flag.risk_reason}")
        
        return "\n".join(risks)
    
    def _format_strategy_context(self, analysis: StrategyAnalysis) -> str:
        """格式化策略分析上下文"""
        status = "✅ 最优策略" if analysis.is_optimal else "⚠️ 非最优策略"
        return f"""{status}
- 情境类型：{analysis.situation_type}
- 用户策略：{analysis.strategy_chosen}
- 销冠策略：{analysis.golden_strategy}
- 分析：{analysis.optimality_reason}"""
    
    def _create_fallback_evaluation(
        self,
        fsm_state: FSMState,
        compliance_result: ComplianceOutput,
    ) -> EvaluatorOutput:
        """创建兜底评估结果"""
        # 根据合规结果调整合规分数
        compliance_score = 8.0 if compliance_result.is_compliant else 4.0
        
        return EvaluatorOutput(
            integrity=DimensionScore(
                score=5.0,
                feedback="系统评估异常，给出中性分数",
                evidence=None,
            ),
            relevance=DimensionScore(
                score=5.0,
                feedback="系统评估异常，给出中性分数",
                evidence=None,
            ),
            correctness=DimensionScore(
                score=5.0,
                feedback="系统评估异常，给出中性分数",
                evidence=None,
            ),
            logic=DimensionScore(
                score=5.0,
                feedback="系统评估异常，给出中性分数",
                evidence=None,
            ),
            compliance=DimensionScore(
                score=compliance_score,
                feedback="基于合规预检结果",
                evidence=None,
            ),
            overall_score=5.0,
            goal_advanced=False,
            goal_feedback="系统评估异常，无法判断目标推进",
            extracted_slots=[],
            improvement_points=["建议继续保持专业态度"],
        )
