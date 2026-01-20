"""
策略分析服务
识别用户策略选择 vs 销冠最优策略
"""
import uuid
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.models.adoption_models import StrategyDecision, UserStrategyProfile
from app.schemas.strategy import (
    StrategyAnalysis,
    SituationType,
    STRATEGY_TAXONOMY,
)
from app.schemas.fsm import SalesStage

logger = logging.getLogger(__name__)


# 情境检测关键词
SITUATION_KEYWORDS: Dict[SituationType, List[str]] = {
    SituationType.PRICE_OBJECTION: ["贵", "价格", "年费", "费用", "成本", "便宜", "优惠"],
    SituationType.TIMING_OBJECTION: ["考虑", "再说", "不急", "以后", "下次", "时间"],
    SituationType.TRUST_OBJECTION: ["不信", "骗", "忽悠", "真的吗", "靠谱", "保证"],
    SituationType.BUDGET_PROBE: ["预算", "多少钱", "价位", "承受", "范围"],
    SituationType.HIDDEN_PAIN: ["困扰", "问题", "麻烦", "痛点", "难题"],
}

# 策略检测关键词
STRATEGY_KEYWORDS: Dict[str, List[str]] = {
    "reframe_value": ["价值", "值得", "回报", "收益", "省", "赚"],
    "compare_competitors": ["对比", "相比", "其他", "竞品", "别家"],
    "offer_tradeoff": ["方案", "选择", "替代", "折中", "调整"],
    "delay_decision": ["考虑", "时间", "不急", "慢慢"],
    "break_down_cost": ["平均", "每天", "每月", "算下来"],
    "roi_calculation": ["投资", "回报", "ROI", "收益率"],
    "social_proof": ["很多人", "客户", "大家", "都在用"],
    "case_study": ["案例", "之前", "成功", "例子"],
    "create_urgency": ["限时", "优惠", "机会", "错过", "名额"],
    "deep_probe": ["具体", "详细", "能说说", "比如"],
    "implication_question": ["影响", "后果", "如果不", "会怎样"],
}

# 策略 -> 动作单元映射 (Action Units)
STRATEGY_ACTION_UNITS: Dict[str, List[str]] = {
    # 价格异议
    "reframe_value": ["acknowledge_concern", "pivot_perspective", "highlight_roi"],
    "compare_competitors": ["acknowledge_competitor", "highlight_differentiation", "prove_superiority"],
    "offer_tradeoff": ["acknowledge_budget", "propose_downgrade", "preserve_core_value"],
    "delay_decision": ["acknowledge_hesitation", "set_followup", "keep_warm"],
    "break_down_cost": ["acknowledge_price", "calculate_daily_cost", "compare_trivial_expense"],
    "roi_calculation": ["request_data", "calculate_return", "show_payback_period"],
    
    # 信任异议
    "social_proof": ["cite_similar_client", "share_results", "offer_reference"],
    "case_study": ["tell_story", "highlight_transformation", "prove_outcome"],
    
    # 痛点挖掘
    "deep_probe": ["ask_open_question", "active_listening", "dig_deeper"],
    "implication_question": ["identify_problem", "explore_consequence", "magnify_pain"],
    
    # 预算探测
    "range_anchor": ["state_industry_norm", "provide_range", "gauge_reaction"],
    "value_first": ["defer_price", "build_value", "ask_budget_later"],
    
    # 通用/未知
    "unknown": ["unknown_action"],
}


class StrategyAnalyzer:
    """
    策略分析器
    
    核心职责：
    1. 识别当前情境类型
    2. 识别用户采用的策略
    3. 判断是否为最优策略
    4. 记录策略决策
    """
    
    def analyze_strategy(
        self,
        user_message: str,
        npc_message: str,
        stage: SalesStage,
        context: Optional[Dict] = None,
    ) -> StrategyAnalysis:
        """
        分析用户的策略选择
        
        Args:
            user_message: 用户输入
            npc_message: NPC 回复（用于情境判断）
            stage: 当前阶段
            context: 上下文
            
        Returns:
            策略分析结果
        """
        # 1. 识别情境类型
        situation_type = self._detect_situation(npc_message, stage)
        
        # 2. 识别用户策略
        strategy_chosen = self._detect_strategy(user_message)
        
        # 2.1 获取 Action Units
        action_units = STRATEGY_ACTION_UNITS.get(strategy_chosen, ["unknown_action"])
        
        # 3. 获取该情境的策略库
        taxonomy = STRATEGY_TAXONOMY.get(situation_type, {})
        available_strategies = taxonomy.get("available", [strategy_chosen])
        golden_strategy = taxonomy.get("golden", strategy_chosen)
        
        # 4. 判断是否最优
        is_optimal = strategy_chosen == golden_strategy
        
        # 5. 生成原因分析
        if is_optimal:
            reason = f"你选择了 {strategy_chosen} 策略，这是销冠在 {situation_type.value} 情境下的最优选择"
        else:
            reason = f"你选择了 {strategy_chosen} 策略，但销冠在 {situation_type.value} 情境下通常使用 {golden_strategy} 策略，效果更好"
        
        return StrategyAnalysis(
            situation_type=situation_type.value,
            strategy_chosen=strategy_chosen,
            action_units=action_units,
            available_strategies=available_strategies,
            is_optimal=is_optimal,
            golden_strategy=golden_strategy,
            optimality_reason=reason,
            confidence=0.8,
        )
    
    def _detect_situation(self, npc_message: str, stage: SalesStage) -> SituationType:
        """检测情境类型"""
        npc_lower = npc_message.lower()
        
        # 基于关键词检测
        max_score = 0
        detected = SituationType.PRICE_OBJECTION  # 默认
        
        for situation, keywords in SITUATION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in npc_lower)
            if score > max_score:
                max_score = score
                detected = situation
        
        # 如果没有明确匹配，基于阶段推断
        if max_score == 0:
            stage_defaults = {
                SalesStage.OPENING: SituationType.COLD_CALL,
                SalesStage.NEEDS_DISCOVERY: SituationType.SURFACE_NEED,
                SalesStage.PRODUCT_INTRO: SituationType.VALUE_PROPOSITION,
                SalesStage.OBJECTION_HANDLING: SituationType.PRICE_OBJECTION,
                SalesStage.CLOSING: SituationType.SOFT_CLOSE,
            }
            detected = stage_defaults.get(stage, SituationType.PRICE_OBJECTION)
        
        return detected
    
    def _detect_strategy(self, user_message: str) -> str:
        """检测用户采用的策略"""
        user_lower = user_message.lower()
        
        max_score = 0
        detected = "unknown"
        
        for strategy, keywords in STRATEGY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in user_lower)
            if score > max_score:
                max_score = score
                detected = strategy
        
        return detected
    
    async def save_strategy_decision(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        turn_id: int,
        analysis: StrategyAnalysis,
        npc_mood_change: float = 0.0,
        goal_progress: bool = False,
        immediate_score: float = 0.0,
    ) -> StrategyDecision:
        """
        保存策略决策记录
        
        【因果闭环核心】
        每一轮用户发言，必须产生 StrategyDecision
        没有 StrategyDecision = 该轮对能力系统无意义
        
        StrategyDecision 是 CurriculumPlanner 的唯一输入之一
        """
        # 从 situation_type 推断 stage
        stage = self._situation_to_stage(analysis.situation_type)
        
        decision = StrategyDecision(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            stage=stage,
            situation_type=analysis.situation_type,
            situation_context=None,
            strategy_chosen=analysis.strategy_chosen,
            available_strategies={"strategies": analysis.available_strategies},
            is_optimal=analysis.is_optimal,
            golden_strategy=analysis.golden_strategy,
            optimality_reason=analysis.optimality_reason,
            immediate_score=immediate_score,
            npc_mood_change=npc_mood_change,
            goal_progress=goal_progress,
        )
        db.add(decision)
        await db.flush()
        
        logger.info(
            f"[StrategyAnalyzer] StrategyDecision saved: id={decision.id}, "
            f"situation={analysis.situation_type}, optimal={analysis.is_optimal}"
        )
        return decision
    
    def _situation_to_stage(self, situation_type: str) -> str:
        """情境类型映射到阶段"""
        stage_mapping = {
            "cold_call": "OPENING",
            "warm_referral": "OPENING",
            "inbound_inquiry": "OPENING",
            "surface_need": "NEEDS_DISCOVERY",
            "hidden_pain": "NEEDS_DISCOVERY",
            "budget_probe": "NEEDS_DISCOVERY",
            "decision_maker_check": "NEEDS_DISCOVERY",
            "feature_demo": "PRODUCT_INTRO",
            "value_proposition": "PRODUCT_INTRO",
            "competitive_comparison": "PRODUCT_INTRO",
            "price_objection": "OBJECTION_HANDLING",
            "timing_objection": "OBJECTION_HANDLING",
            "trust_objection": "OBJECTION_HANDLING",
            "competitor_objection": "OBJECTION_HANDLING",
            "authority_objection": "OBJECTION_HANDLING",
            "soft_close": "CLOSING",
            "hard_close": "CLOSING",
            "trial_close": "CLOSING",
        }
        return stage_mapping.get(situation_type, "UNKNOWN")
    
    @staticmethod
    async def get_strategy_deviation_stats(
        db: AsyncSession,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        统计用户策略偏离模式
        回答：用户在哪些情境下最常偏离销冠策略？
        """
        query = select(
            StrategyDecision.situation_type,
            StrategyDecision.strategy_chosen,
            StrategyDecision.golden_strategy,
            func.count(StrategyDecision.id).label("total_count"),
            func.sum(func.cast(StrategyDecision.is_optimal, Integer)).label("optimal_count"),
        ).where(
            StrategyDecision.user_id == user_id
        ).group_by(
            StrategyDecision.situation_type,
            StrategyDecision.strategy_chosen,
            StrategyDecision.golden_strategy,
        ).order_by(
            func.count(StrategyDecision.id).desc()
        ).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "situation_type": row.situation_type,
                "strategy_chosen": row.strategy_chosen,
                "golden_strategy": row.golden_strategy,
                "total_decisions": row.total_count,
                "optimal_decisions": row.optimal_count or 0,
                "optimal_rate": (row.optimal_count or 0) / row.total_count if row.total_count > 0 else 0,
                "is_deviation": row.strategy_chosen != row.golden_strategy,
            }
            for row in rows
        ]
    
    @staticmethod
    async def get_user_strategy_profile(
        db: AsyncSession,
        user_id: str,
    ) -> Dict:
        """
        获取用户策略画像
        """
        # 按情境统计最优率
        situation_query = select(
            StrategyDecision.situation_type,
            func.count(StrategyDecision.id).label("total"),
            func.sum(func.cast(StrategyDecision.is_optimal, Integer)).label("optimal"),
        ).where(
            StrategyDecision.user_id == user_id
        ).group_by(
            StrategyDecision.situation_type
        )
        
        result = await db.execute(situation_query)
        situation_stats = result.all()
        
        # 计算各情境最优率
        optimal_rate_by_situation = {}
        weakness_situations = []
        
        for row in situation_stats:
            rate = (row.optimal or 0) / row.total if row.total > 0 else 0
            optimal_rate_by_situation[row.situation_type] = rate
            if rate < 0.5 and row.total >= 3:
                weakness_situations.append({
                    "situation": row.situation_type,
                    "optimal_rate": rate,
                    "sample_size": row.total,
                })
        
        # 按弱点排序
        weakness_situations.sort(key=lambda x: x["optimal_rate"])
        
        return {
            "user_id": user_id,
            "optimal_rate_by_situation": optimal_rate_by_situation,
            "top_weakness_situations": weakness_situations[:5],
            "overall_optimal_rate": sum(optimal_rate_by_situation.values()) / len(optimal_rate_by_situation) if optimal_rate_by_situation else 0,
        }
