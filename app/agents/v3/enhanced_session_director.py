"""
Enhanced Session Director V3 - 增强版会话控制器
集成 ReAct 推理引擎、动态重要性计算、语义风险检测

向后兼容原有 SessionDirectorV3，同时支持新能力
"""
import logging
from typing import Dict, Any, Optional, List

from app.agents.v3.session_director_v3 import SessionDirectorV3
from app.agents.v3.react_reasoning_engine import (
    ReActReasoningEngine,
    ReActConfig,
    ReActResult,
    convert_react_to_turn_plan,
)
from app.agents.v3.dynamic_importance_calculator import (
    DynamicImportanceCalculator,
    ImportanceResult,
    create_calculator,
)
from app.agents.v3.semantic_risk_detector import (
    SemanticRiskDetector,
    RiskDetectionResult,
    RiskAction,
    create_detector,
)
from app.schemas.v3_agent_outputs import TurnPlan
from app.schemas.fsm import FSMState
from app.services.model_gateway import ModelGateway
from app.services.model_gateway.budget import BudgetManager
from app.core.interaction_config import get_config_manager, get_react_config

logger = logging.getLogger(__name__)


class EnhancedSessionDirectorV3(SessionDirectorV3):
    """
    增强版 Session Director V3

    新增能力:
    - ReAct 智能推理 (替代硬编码决策)
    - 动态重要性计算 (替代静态权重)
    - 语义风险检测 (替代关键词匹配)
    - 可配置模式 (简单/增强)
    """

    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
        enable_react: bool = True,
        enable_dynamic_importance: bool = True,
        enable_semantic_risk: bool = True,
        react_config: Optional[ReActConfig] = None,
        embedding_fn=None,
    ):
        super().__init__(model_gateway, budget_manager)

        # 功能开关
        self.enable_react = enable_react
        self.enable_dynamic_importance = enable_dynamic_importance
        self.enable_semantic_risk = enable_semantic_risk

        # 初始化增强组件
        if enable_react:
            config = react_config or get_react_config()
            self.react_engine = ReActReasoningEngine(
                model_gateway=model_gateway,
                config=config,
            )
        else:
            self.react_engine = None

        if enable_dynamic_importance:
            self.importance_calculator = create_calculator()
        else:
            self.importance_calculator = None

        if enable_semantic_risk:
            self.risk_detector = create_detector(embedding_fn=embedding_fn)
        else:
            self.risk_detector = None

        logger.info(
            f"EnhancedSessionDirectorV3 initialized: "
            f"react={enable_react}, "
            f"dynamic_importance={enable_dynamic_importance}, "
            f"semantic_risk={enable_semantic_risk}"
        )

    async def plan_turn(
        self,
        turn_number: int,
        fsm_state: FSMState,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        session_id: str,
        user_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> TurnPlan:
        """
        规划本轮执行计划 (增强版)

        流程:
        1. 语义风险检测 → 可能提前阻断或降级
        2. 动态重要性计算 → 替代静态权重
        3. ReAct 推理 → 智能决策
        4. 整合输出 → TurnPlan
        """
        # ===== Phase 1: 语义风险检测 =====
        risk_result: Optional[RiskDetectionResult] = None
        if self.enable_semantic_risk:
            risk_result = self.risk_detector.detect(user_message)

            # 如果需要阻断
            if risk_result.recommended_action == RiskAction.BLOCK:
                logger.warning(f"[EnhancedDirector] Risk blocked: {risk_result.explanation}")
                return self._create_blocked_plan(turn_number, risk_result)

        # ===== Phase 2: 动态重要性计算 =====
        importance_result: Optional[ImportanceResult] = None
        if self.enable_dynamic_importance:
            importance_result = self.importance_calculator.calculate(
                turn_number=turn_number,
                fsm_state=fsm_state,
                user_message=user_message,
                conversation_history=conversation_history,
                user_profile=user_profile,
            )
            logger.info(
                f"[EnhancedDirector] Importance: "
                f"{importance_result.importance_score:.2f} "
                f"(baseline: {importance_result.baseline_importance:.2f}, "
                f"delta: {importance_result.delta_from_baseline:+.2f})"
            )

        # ===== Phase 3: ReAct 推理 或 原有逻辑 =====
        if self.enable_react:
            budget_remaining = self.budget_manager.get_remaining_budget(session_id)

            react_result = await self.react_engine.reason(
                turn_number=turn_number,
                fsm_state=fsm_state,
                user_message=user_message,
                conversation_history=conversation_history,
                session_id=session_id,
                user_id=user_id,
                budget_remaining=budget_remaining,
                context={
                    "importance": importance_result.model_dump() if importance_result else None,
                    "risk": risk_result.model_dump() if risk_result else None,
                },
            )

            # 转换为 TurnPlan
            plan_dict = convert_react_to_turn_plan(react_result)

            # 应用风险调整
            if risk_result and risk_result.recommended_action == RiskAction.DOWNGRADE:
                plan_dict["model_upgrade"] = False
                plan_dict["risk_level"] = "high"

            return TurnPlan(**plan_dict)

        else:
            # 使用原有逻辑
            return await super().plan_turn(
                turn_number=turn_number,
                fsm_state=fsm_state,
                user_message=user_message,
                conversation_history=conversation_history,
                session_id=session_id,
                user_id=user_id,
            )

    def _create_blocked_plan(
        self,
        turn_number: int,
        risk_result: RiskDetectionResult,
    ) -> TurnPlan:
        """创建阻断计划"""
        return TurnPlan(
            turn_number=turn_number,
            path_mode="fast",
            agents_to_call=["compliance_responder"],  # 特殊合规响应
            budget_allocation={"compliance_responder": 0.001},
            model_upgrade=False,
            risk_level="critical",
            evidence_confidence=0.0,
            reasoning=f"Blocked due to risk: {risk_result.primary_category.value}",
        )

    def get_diagnostics(self) -> Dict[str, Any]:
        """获取诊断信息"""
        diagnostics = {
            "mode": "enhanced",
            "features": {
                "react": self.enable_react,
                "dynamic_importance": self.enable_dynamic_importance,
                "semantic_risk": self.enable_semantic_risk,
            },
        }

        if self.risk_detector:
            diagnostics["risk_detector_stats"] = self.risk_detector.get_statistics()

        if self.importance_calculator:
            diagnostics["importance_weights"] = self.importance_calculator.get_weight_summary()

        return diagnostics


# ============================================================
# Factory Functions
# ============================================================

def create_enhanced_director(
    model_gateway: ModelGateway,
    budget_manager: BudgetManager,
    mode: str = "enhanced",  # "simple", "enhanced", "full"
    embedding_fn=None,
) -> EnhancedSessionDirectorV3:
    """
    创建增强版 Session Director

    模式:
    - simple: 仅原有功能
    - enhanced: 动态重要性 + 语义风险
    - full: 全部功能 (ReAct + 动态重要性 + 语义风险)
    """
    if mode == "simple":
        return EnhancedSessionDirectorV3(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            enable_react=False,
            enable_dynamic_importance=False,
            enable_semantic_risk=False,
        )
    elif mode == "enhanced":
        return EnhancedSessionDirectorV3(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            enable_react=False,
            enable_dynamic_importance=True,
            enable_semantic_risk=True,
            embedding_fn=embedding_fn,
        )
    else:  # full
        return EnhancedSessionDirectorV3(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            enable_react=True,
            enable_dynamic_importance=True,
            enable_semantic_risk=True,
            embedding_fn=embedding_fn,
        )


def upgrade_director(
    original: SessionDirectorV3,
    mode: str = "enhanced",
) -> EnhancedSessionDirectorV3:
    """
    升级现有 Director 为增强版

    用于渐进式迁移
    """
    return create_enhanced_director(
        model_gateway=original.model_gateway,
        budget_manager=original.budget_manager,
        mode=mode,
    )
