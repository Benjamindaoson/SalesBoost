"""
Coach Tactical Agent
回合级战术指导，输出结构化建议
+ 策略级指导：基于销冠策略给出升级建议
"""
import logging
from typing import Dict, Any, List, Optional, Type

from app.core.llm_context import LLMCallContext
from pydantic import BaseModel

from app.agents.roles.base import BaseAgent
from app.schemas.agent_outputs import CoachOutput, RAGOutput, ComplianceOutput
from app.schemas.fsm import FSMState, SalesStage
from app.schemas.strategy import StrategyAnalysis, StrategyGuidance, STRATEGY_TAXONOMY

logger = logging.getLogger(__name__)


class CoachAgent(BaseAgent):
    """
    销售教练 Agent
    
    核心职责：
    - 提供回合级战术指导
    - 基于当前 FSM 阶段给出针对性建议
    - 输出结构化的 JSON 格式
    - 结合 RAG 检索结果和合规检查结果
    
    输出格式：
    {
        "suggestion": "具体建议",
        "reasoning": "建议理由",
        "example_utterance": "示例话术",
        "priority": "high/medium/low",
        "technique_name": "使用的销售技巧",
        "stage_alignment": true/false,
        "confidence": 0.0-1.0
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(temperature=0.2, **kwargs)  # 教练需要确定性

    AGENT_TYPE = "coach"
    
    @property
    def system_prompt(self) -> str:
        try:
            with open("app/prompts/coach_prompt.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            # Fallback if file not found
            return """你是 SalesBoost 系统的【金牌销售教练】，专门提供回合级战术指导。
            ... (fallback content) ...
            """
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return CoachOutput
    
    async def generate_advice(
        self,
        user_message: str,
        npc_response: str,
        conversation_history: List[Dict[str, Any]],
        fsm_state: FSMState,
        rag_content: RAGOutput,
        compliance_result: ComplianceOutput,
        strategy_analysis: Optional[StrategyAnalysis] = None,
        llm_context: Optional["LLMCallContext"] = None,
    ) -> tuple[CoachOutput, Optional[StrategyGuidance]]:
        """
        生成教练建议
        
        Args:
            user_message: 销售员输入
            npc_response: NPC 回复
            conversation_history: 对话历史
            fsm_state: 当前 FSM 状态
            rag_content: RAG 检索结果
            compliance_result: 合规检查结果
            strategy_analysis: 策略分析结果（可选）
            
        Returns:
            (教练建议输出, 策略级指导)
        """
        # 构建对话历史
        history_str = self._format_conversation_history(conversation_history)
        
        # 构建 RAG 参考内容
        rag_str = self._format_rag_content(rag_content)
        
        # 构建合规提示
        compliance_str = self._format_compliance_result(compliance_result)
        
        # 获取当前阶段目标
        stage_goal = self._get_stage_goal(fsm_state.current_stage)
        
        # 获取缺失 Slot
        missing_slots = self._get_missing_slots_description(fsm_state)
        
        # 策略分析上下文
        strategy_str = self._format_strategy_analysis(strategy_analysis)
        
        user_prompt = f"""【当前状态】
- 销售阶段：{fsm_state.current_stage.value}
- 阶段目标：{stage_goal}
- 客户情绪：{fsm_state.npc_mood:.2f}
- 对话轮次：{fsm_state.turn_count}
- 缺失信息：{missing_slots}

【对话历史】
{history_str}

【销售员最新输入】
{user_message}

【客户回复】
{npc_response}

【参考话术/案例】
{rag_str}

【合规检查】
{compliance_str}

【策略分析】
{strategy_str}

请分析销售员的表现，并给出针对性的战术建议。如果策略非最优，请重点指导如何过渡到销冠策略。"""
        
        try:
            result = await self.invoke_with_parser(user_prompt, llm_context=llm_context)
            
            # 生成策略级指导
            strategy_guidance = None
            if strategy_analysis and not strategy_analysis.is_optimal:
                strategy_guidance = self._generate_strategy_guidance(
                    strategy_analysis,
                    result,
                )
            
            return result, strategy_guidance
        except Exception as e:
            logger.error(f"Coach advice generation failed: {e}")
            # 返回兜底建议
            return CoachOutput(
                suggestion="继续保持专业态度，倾听客户需求",
                reasoning="系统分析中出现异常，给出通用建议",
                example_utterance="我理解您的想法，能否再详细说说您的具体需求？",
                priority="medium",
                technique_name="主动倾听",
                stage_alignment=True,
                confidence=0.5,
            ), None
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        if not history:
            return "（无历史对话）"
        
        formatted = []
        for msg in history[-8:]:  # 最近 8 条
            role = "销售员" if msg["role"] == "user" else "客户"
            formatted.append(f"{role}：{msg['content']}")
        
        return "\n".join(formatted)
    
    def _format_rag_content(self, rag_output: RAGOutput) -> str:
        """格式化 RAG 内容"""
        if not rag_output.retrieved_content:
            return "（无参考内容）"
        
        formatted = []
        for item in rag_output.retrieved_content[:3]:  # 最多 3 条
            sources = ", ".join(item.source_citations) if item.source_citations else "未知来源"
            formatted.append(f"- {item.content}\n  来源：{sources}")
        
        return "\n".join(formatted)
    
    def _format_compliance_result(self, result: ComplianceOutput) -> str:
        """格式化合规结果"""
        if result.is_compliant:
            return "✅ 合规检查通过"
        
        risks = []
        for flag in result.risk_flags:
            risks.append(f"⚠️ {flag.risk_type}: {flag.risk_reason}")
            if flag.safe_alternative:
                risks.append(f"   建议替换为：{flag.safe_alternative}")
        
        return "\n".join(risks)
    
    def _get_stage_goal(self, stage: SalesStage) -> str:
        """获取阶段目标描述"""
        goals = {
            SalesStage.OPENING: "建立信任关系，获取客户基本信息",
            SalesStage.NEEDS_DISCOVERY: "挖掘客户核心需求和痛点",
            SalesStage.PRODUCT_INTRO: "针对需求介绍产品价值",
            SalesStage.OBJECTION_HANDLING: "有效处理客户异议",
            SalesStage.CLOSING: "推动成交或明确下一步",
            SalesStage.COMPLETED: "训练已完成",
        }
        return goals.get(stage, "未知阶段")
    
    def _get_missing_slots_description(self, fsm_state: FSMState) -> str:
        """获取缺失 Slot 描述"""
        # 从 FSM 状态中获取缺失的 Slot
        coverage = fsm_state.stage_coverages.get(fsm_state.current_stage.value)
        if not coverage:
            return "无"
        
        missing_count = coverage.required_total - coverage.required_filled
        if missing_count <= 0:
            return "无（已收集完整）"
        
        return f"还需收集 {missing_count} 项关键信息"
    
    def _format_strategy_analysis(self, analysis: Optional[StrategyAnalysis]) -> str:
        """格式化策略分析"""
        if not analysis:
            return "（无策略分析）"
        
        status = "✅ 最优策略" if analysis.is_optimal else "⚠️ 非最优策略"
        return f"""{status}
- 情境类型：{analysis.situation_type}
- 用户策略：{analysis.strategy_chosen}
- 销冠策略：{analysis.golden_strategy}
- 分析：{analysis.optimality_reason}"""
    
    def _generate_strategy_guidance(
        self,
        analysis: StrategyAnalysis,
        coach_output: CoachOutput,
    ) -> StrategyGuidance:
        """生成策略级指导"""
        # 策略中文映射
        strategy_cn = {
            "reframe_value": "价值重塑",
            "compare_competitors": "竞品对比",
            "offer_tradeoff": "方案折中",
            "break_down_cost": "成本分摊",
            "roi_calculation": "ROI 计算",
            "social_proof": "社会证明",
            "case_study": "案例分享",
            "create_urgency": "紧迫感创造",
            "cost_of_delay": "延迟成本",
            "implication_question": "影响式提问",
            "deep_probe": "深度探询",
            "range_anchor": "区间锚定",
            "unknown": "未识别策略",
        }
        
        current_cn = strategy_cn.get(analysis.strategy_chosen, analysis.strategy_chosen)
        golden_cn = strategy_cn.get(analysis.golden_strategy, analysis.golden_strategy)
        
        # 生成过渡建议
        transition_templates = {
            ("unknown", "reframe_value"): "先认可客户的顾虑，然后将话题引导到产品能带来的具体价值上",
            ("compare_competitors", "reframe_value"): "不要只强调比竞品好，而是聚焦于我们能为客户创造的独特价值",
            ("delay_decision", "reframe_value"): "不要给客户拖延的借口，而是让客户看到现在行动的价值",
            ("break_down_cost", "reframe_value"): "除了分摊成本，更要强调投入产出比和长期价值",
        }
        
        transition_key = (analysis.strategy_chosen, analysis.golden_strategy)
        transition = transition_templates.get(
            transition_key,
            f"从【{current_cn}】策略过渡到【{golden_cn}】策略，关键是改变对话的焦点"
        )
        
        # 生成示例话术
        example_templates = {
            "reframe_value": "王总，我理解您对价格的考虑。不过让我帮您算一笔账：这张卡每年能为您节省的机场贵宾厅费用、酒店升级费用，加起来远超年费。更重要的是，它能帮您节省宝贵的时间。",
            "case_study": "王总，我有一位客户跟您情况很像，一开始也觉得年费高。但用了半年后，他跟我说光是出差省下的时间和精力，就值回票价了。",
            "cost_of_delay": "王总，现在这个优惠活动月底就结束了。如果您现在不决定，下个月再办就要多付 500 元了。",
            "implication_question": "王总，如果继续用现在的卡，每次出差排队值机、等候安检，一年下来要浪费多少时间呢？",
        }
        
        example = example_templates.get(
            analysis.golden_strategy,
            coach_output.example_utterance
        )
        
        return StrategyGuidance(
            current_strategy=current_cn,
            current_strategy_analysis=f"你当前使用的是【{current_cn}】策略，{analysis.optimality_reason}",
            golden_strategy=golden_cn,
            why_golden_better=f"销冠在【{analysis.situation_type}】情境下通常使用【{golden_cn}】策略，因为它能更有效地化解客户顾虑并推进成交",
            transition_suggestion=transition,
            example_utterance=example,
        )
