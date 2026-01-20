"""
Report Service
生成训练报告 - 包含销冠能力复制系统分析
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.reports import (
    TrainingReport,
    SessionSummary,
    RadarChartData,
    StagePerformance,
    TurnDetail,
    StrategyComparison,
    EffectiveSuggestion,
    CurriculumRecommendation,
)
from app.schemas.fsm import SalesStage
from app.models.runtime_models import Session, Message
from app.services.adoption_tracker import AdoptionTracker
from app.services.strategy_analyzer import StrategyAnalyzer
from app.services.curriculum_planner import CurriculumPlanner

logger = logging.getLogger(__name__)

STAGE_NAME_CN = {
    "OPENING": "破冰建联",
    "NEEDS_DISCOVERY": "需求挖掘",
    "PRODUCT_INTRO": "产品介绍",
    "OBJECTION_HANDLING": "异议处理",
    "CLOSING": "促单成交",
    "COMPLETED": "训练完成",
}

SITUATION_NAME_CN = {
    "price_objection": "价格异议",
    "timing_objection": "时机异议",
    "trust_objection": "信任异议",
    "competitor_objection": "竞品异议",
    "authority_objection": "决策权异议",
    "budget_probe": "预算探测",
    "hidden_pain": "隐藏痛点挖掘",
    "cold_call": "陌生拜访",
    "warm_referral": "转介绍",
    "soft_close": "软促单",
    "hard_close": "硬促单",
    "surface_need": "表面需求",
    "value_proposition": "价值主张",
}

TECHNIQUE_NAME_CN = {
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
    "SPIN提问法": "SPIN提问法",
    "FAB法则": "FAB法则",
    "Feel-Felt-Found": "Feel-Felt-Found",
    "主动倾听": "主动倾听",
}


class ReportService:
    """训练报告生成服务 - 包含销冠能力复制系统分析"""
    
    def __init__(self):
        self.curriculum_planner = CurriculumPlanner()
    
    async def generate_report(
        self,
        session: Session,
        messages: List[Message],
        db: Optional[AsyncSession] = None,
        include_turn_details: bool = False,
        include_champion_analysis: bool = True,
    ) -> TrainingReport:
        """
        生成训练报告
        
        Args:
            session: 会话对象
            messages: 消息列表
            db: 数据库会话（用于查询策略和采纳数据）
            include_turn_details: 是否包含轮次详情
            include_champion_analysis: 是否包含销冠能力分析
            
        Returns:
            训练报告
        """
        logger.info(f"Generating report for session: {session.id}")
        
        # 计算五维平均分
        dimension_scores = self._calculate_dimension_averages(messages)
        
        # 生成雷达图数据
        radar_chart = RadarChartData(
            values=[
                dimension_scores.get("integrity", 5.0),
                dimension_scores.get("relevance", 5.0),
                dimension_scores.get("correctness", 5.0),
                dimension_scores.get("logic", 5.0),
                dimension_scores.get("compliance", 5.0),
            ]
        )
        
        # 计算阶段表现
        stage_performances = self._calculate_stage_performances(messages)
        
        # 生成摘要
        summary = self._generate_summary(session, messages)
        
        # 生成改进建议
        strengths, improvements, focus = self._generate_recommendations(
            dimension_scores, stage_performances
        )
        
        # 轮次详情（可选）
        turn_details = None
        if include_turn_details:
            turn_details = self._extract_turn_details(messages)
        
        # 计算总分
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        # ========== 销冠能力复制系统分析 ==========
        strategy_comparisons = None
        overall_optimal_rate = None
        effective_suggestions = None
        adoption_rate = None
        effective_adoption_rate = None
        curriculum_recommendations = None
        
        if include_champion_analysis and db:
            # 策略对比分析
            strategy_comparisons, overall_optimal_rate = await self._analyze_strategy_comparisons(
                db, session.user_id
            )
            
            # 有效建议统计
            effective_suggestions, adoption_rate, effective_adoption_rate = await self._analyze_effective_suggestions(
                db, session.user_id
            )
            
            # 训练推荐
            curriculum_recommendations = await self._generate_curriculum_recommendations(
                db, session.user_id
            )
        
        return TrainingReport(
            summary=summary,
            overall_score=round(overall_score, 2),
            radar_chart=radar_chart,
            dimension_scores=dimension_scores,
            dimension_feedback=self._generate_dimension_feedback(dimension_scores),
            stage_performances=stage_performances,
            turn_details=turn_details,
            top_strengths=strengths,
            top_improvements=improvements,
            recommended_focus=focus,
            # 销冠能力复制系统
            strategy_comparisons=strategy_comparisons,
            overall_optimal_rate=overall_optimal_rate,
            effective_suggestions=effective_suggestions,
            adoption_rate=adoption_rate,
            effective_adoption_rate=effective_adoption_rate,
            curriculum_recommendations=curriculum_recommendations,
            generated_at=datetime.utcnow(),
        )

    def _calculate_dimension_averages(self, messages: List[Message]) -> Dict[str, float]:
        """计算五维平均分"""
        dimensions = ["integrity", "relevance", "correctness", "logic", "compliance"]
        totals = {d: 0.0 for d in dimensions}
        counts = {d: 0 for d in dimensions}
        
        for msg in messages:
            if msg.dimension_scores:
                for dim in dimensions:
                    if dim in msg.dimension_scores:
                        totals[dim] += msg.dimension_scores[dim]
                        counts[dim] += 1
        
        return {
            dim: round(totals[dim] / counts[dim], 2) if counts[dim] > 0 else 5.0
            for dim in dimensions
        }
    
    def _calculate_stage_performances(self, messages: List[Message]) -> List[StagePerformance]:
        """计算各阶段表现"""
        stage_data: Dict[str, Dict] = {}
        
        for msg in messages:
            stage = msg.stage
            if stage not in stage_data:
                stage_data[stage] = {
                    "turns": 0,
                    "scores": [],
                    "goal_achieved": False,
                    "achievements": [],
                    "improvements": [],
                }
            
            stage_data[stage]["turns"] += 1
            if msg.turn_score:
                stage_data[stage]["scores"].append(msg.turn_score)
            
            if msg.evaluator_result:
                if msg.evaluator_result.get("goal_advanced"):
                    stage_data[stage]["goal_achieved"] = True
                if msg.evaluator_result.get("improvement_points"):
                    stage_data[stage]["improvements"].extend(
                        msg.evaluator_result["improvement_points"][:2]
                    )
        
        performances = []
        for stage, data in stage_data.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 5.0
            performances.append(StagePerformance(
                stage=stage,
                stage_name_cn=STAGE_NAME_CN.get(stage, stage),
                turns_spent=data["turns"],
                avg_score=round(avg_score, 2),
                goal_achieved=data["goal_achieved"],
                slot_coverage=0.0,
                key_achievements=data["achievements"][:3],
                improvement_areas=list(set(data["improvements"]))[:3],
            ))
        
        return performances
    
    def _generate_summary(self, session: Session, messages: List[Message]) -> SessionSummary:
        """生成会话摘要"""
        duration = 0
        if session.completed_at and session.started_at:
            duration = int((session.completed_at - session.started_at).total_seconds() / 60)
        
        # 计算完成度
        stages_reached = set(msg.stage for msg in messages)
        all_stages = ["OPENING", "NEEDS_DISCOVERY", "PRODUCT_INTRO", "OBJECTION_HANDLING", "CLOSING"]
        completion_rate = len(stages_reached.intersection(all_stages)) / len(all_stages) * 100
        
        return SessionSummary(
            session_id=session.id,
            user_id=session.user_id,
            scenario_name="",
            persona_name="",
            started_at=session.started_at,
            completed_at=session.completed_at,
            duration_minutes=duration,
            total_turns=len(messages),
            final_stage=session.final_stage or "OPENING",
            completion_rate=round(completion_rate, 1),
        )

    def _generate_recommendations(
        self,
        dimension_scores: Dict[str, float],
        stage_performances: List[StagePerformance],
    ) -> tuple[List[str], List[str], str]:
        """生成改进建议"""
        # 找出强项（分数 >= 7）
        strengths = []
        dim_names = {
            "integrity": "信息完整性",
            "relevance": "回复相关性",
            "correctness": "信息准确性",
            "logic": "表达逻辑性",
            "compliance": "话术合规性",
        }
        
        for dim, score in dimension_scores.items():
            if score >= 7.0:
                strengths.append(f"{dim_names.get(dim, dim)}表现优秀 ({score}分)")
        
        # 找出弱项（分数 < 6）
        improvements = []
        weakest_dim = min(dimension_scores, key=dimension_scores.get)
        
        for dim, score in dimension_scores.items():
            if score < 6.0:
                improvements.append(f"建议加强{dim_names.get(dim, dim)} (当前 {score}分)")
        
        # 推荐重点
        focus = f"建议重点提升【{dim_names.get(weakest_dim, weakest_dim)}】能力"
        
        if not strengths:
            strengths = ["整体表现稳定，继续保持"]
        if not improvements:
            improvements = ["各维度表现均衡，可尝试更高难度场景"]
        
        return strengths[:3], improvements[:3], focus
    
    def _generate_dimension_feedback(self, dimension_scores: Dict[str, float]) -> Dict[str, str]:
        """生成各维度反馈"""
        feedback = {}
        
        thresholds = [
            (8.0, "优秀"),
            (6.0, "良好"),
            (4.0, "需改进"),
            (0.0, "较弱"),
        ]
        
        for dim, score in dimension_scores.items():
            for threshold, label in thresholds:
                if score >= threshold:
                    feedback[dim] = f"{label} ({score}分)"
                    break
        
        return feedback
    
    def _extract_turn_details(self, messages: List[Message]) -> List[TurnDetail]:
        """提取轮次详情"""
        details = []
        user_msg = None
        
        for msg in messages:
            if msg.role == "user":
                user_msg = msg
            elif msg.role == "npc" and user_msg:
                details.append(TurnDetail(
                    turn_number=msg.turn_number,
                    user_message=user_msg.content,
                    npc_response=msg.content,
                    stage=msg.stage,
                    scores=msg.dimension_scores or {},
                    overall_score=msg.turn_score or 5.0,
                    coach_suggestion=msg.coach_result.get("suggestion", "") if msg.coach_result else "",
                    compliance_passed=msg.compliance_result.get("is_compliant", True) if msg.compliance_result else True,
                ))
                user_msg = None
        
        return details
    
    # ========== 销冠能力复制系统分析方法 ==========
    
    async def _analyze_strategy_comparisons(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> tuple[List[StrategyComparison], float]:
        """
        分析策略对比
        回答：用户在哪些情境下偏离销冠策略？
        """
        deviation_stats = await StrategyAnalyzer.get_strategy_deviation_stats(db, user_id)
        
        comparisons = []
        total_decisions = 0
        total_optimal = 0
        
        for stat in deviation_stats:
            situation = stat["situation_type"]
            comparisons.append(StrategyComparison(
                situation_type=situation,
                situation_name_cn=SITUATION_NAME_CN.get(situation, situation),
                your_strategy=stat["strategy_chosen"],
                champion_strategy=stat["golden_strategy"],
                is_optimal=not stat["is_deviation"],
                occurrence_count=stat["total_decisions"],
                optimal_rate=stat["optimal_rate"],
            ))
            total_decisions += stat["total_decisions"]
            total_optimal += stat["optimal_decisions"]
        
        overall_optimal_rate = total_optimal / total_decisions if total_decisions > 0 else 0
        
        return comparisons, round(overall_optimal_rate, 2)
    
    async def _analyze_effective_suggestions(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> tuple[List[EffectiveSuggestion], float, float]:
        """
        分析有效建议
        回答：哪 3 类 Coach 建议最容易让新手变强？
        """
        stats = await AdoptionTracker.get_effective_suggestions_stats(db, user_id, limit=5)
        
        suggestions = []
        total_adoptions = 0
        total_effective = 0
        
        for stat in stats:
            technique = stat["technique"]
            suggestions.append(EffectiveSuggestion(
                technique_name=technique or "unknown",
                technique_name_cn=TECHNIQUE_NAME_CN.get(technique, technique or "未知技巧"),
                total_adoptions=stat["total_adoptions"],
                effective_adoptions=stat["effective_adoptions"],
                effectiveness_rate=stat["effectiveness_rate"],
                avg_skill_improvement=stat["avg_effectiveness_score"],
            ))
            total_adoptions += stat["total_adoptions"]
            total_effective += stat["effective_adoptions"]
        
        # 计算整体采纳率（需要额外查询总建议数）
        # 这里简化处理，使用已采纳的数据
        adoption_rate = 0.0  # 需要从 AdoptionTracker 获取
        effective_adoption_rate = total_effective / total_adoptions if total_adoptions > 0 else 0
        
        return suggestions, adoption_rate, round(effective_adoption_rate, 2)
    
    async def _generate_curriculum_recommendations(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> List[CurriculumRecommendation]:
        """
        生成训练推荐
        回答：为什么推荐这个训练场景？
        """
        curriculum = await self.curriculum_planner.generate_curriculum(db, user_id, max_focus_items=3)
        
        recommendations = []
        for focus in curriculum.next_training_plan:
            expected_improvement = curriculum.expected_improvement.get(focus.focus_situation, 0.1)
            recommendations.append(CurriculumRecommendation(
                focus_situation=SITUATION_NAME_CN.get(focus.focus_situation, focus.focus_situation),
                focus_strategy=TECHNIQUE_NAME_CN.get(focus.focus_strategy, focus.focus_strategy),
                difficulty=focus.difficulty,
                reasoning=curriculum.reasoning,
                expected_improvement=expected_improvement,
            ))
        
        return recommendations
