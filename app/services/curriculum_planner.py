"""
Curriculum Planner - 训练课程规划器
基于用户策略画像和采纳效果，推荐下一步训练计划
"""
import uuid
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.models.adoption_models import (
    AdoptionRecord,
    StrategyDecision,
    UserStrategyProfile,
)
from app.schemas.strategy import (
    CurriculumPlan,
    TrainingFocus,
    SituationType,
    STRATEGY_TAXONOMY,
)

logger = logging.getLogger(__name__)


# 情境难度映射
SITUATION_DIFFICULTY: Dict[str, str] = {
    SituationType.COLD_CALL.value: "hard",
    SituationType.WARM_REFERRAL.value: "easy",
    SituationType.INBOUND_INQUIRY.value: "easy",
    SituationType.SURFACE_NEED.value: "easy",
    SituationType.HIDDEN_PAIN.value: "medium",
    SituationType.BUDGET_PROBE.value: "medium",
    SituationType.DECISION_MAKER_CHECK.value: "medium",
    SituationType.FEATURE_DEMO.value: "easy",
    SituationType.VALUE_PROPOSITION.value: "medium",
    SituationType.COMPETITIVE_COMPARISON.value: "hard",
    SituationType.PRICE_OBJECTION.value: "hard",
    SituationType.TIMING_OBJECTION.value: "medium",
    SituationType.TRUST_OBJECTION.value: "hard",
    SituationType.COMPETITOR_OBJECTION.value: "hard",
    SituationType.AUTHORITY_OBJECTION.value: "medium",
    SituationType.SOFT_CLOSE.value: "medium",
    SituationType.HARD_CLOSE.value: "hard",
    SituationType.TRIAL_CLOSE.value: "easy",
}

# 情境对应的 NPC 人设特征
SITUATION_PERSONA_TRAITS: Dict[str, List[str]] = {
    SituationType.PRICE_OBJECTION.value: ["价格敏感", "精打细算", "比价型"],
    SituationType.TIMING_OBJECTION.value: ["犹豫不决", "拖延型", "需要推动"],
    SituationType.TRUST_OBJECTION.value: ["怀疑型", "谨慎", "需要证据"],
    SituationType.BUDGET_PROBE.value: ["预算有限", "需要审批", "成本导向"],
    SituationType.HIDDEN_PAIN.value: ["内敛", "不善表达", "需要引导"],
    SituationType.COMPETITOR_OBJECTION.value: ["已有供应商", "忠诚度高", "比较型"],
}

# 阶段对应的重点 Slot
STAGE_FOCUS_SLOTS: Dict[str, List[str]] = {
    "OPENING": ["customer_name", "customer_role", "initial_interest"],
    "NEEDS_DISCOVERY": ["pain_point", "budget", "timeline", "decision_maker"],
    "PRODUCT_INTRO": ["value_proposition", "feature_benefit_link"],
    "OBJECTION_HANDLING": ["objection_type", "objection_resolved"],
    "CLOSING": ["commitment", "next_step", "deal_closed"],
}


class CurriculumPlanner:
    """
    训练课程规划器
    
    核心职责：
    1. 分析用户策略画像
    2. 识别最需要提升的情境
    3. 生成个性化训练计划
    4. 回答：为什么推荐这个训练场景？
    """
    
    async def generate_curriculum(
        self,
        db: AsyncSession,
        user_id: str,
        max_focus_items: int = 3,
    ) -> CurriculumPlan:
        """
        生成训练课程计划
        
        Args:
            db: 数据库会话
            user_id: 用户 ID
            max_focus_items: 最大训练焦点数
            
        Returns:
            训练计划
        """
        # 1. 获取用户策略偏离统计
        deviation_stats = await self._get_deviation_stats(db, user_id)
        
        # 2. 获取用户采纳效果统计
        adoption_stats = await self._get_adoption_stats(db, user_id)
        
        # 3. 识别弱点情境
        weakness_situations = self._identify_weaknesses(deviation_stats)
        
        # 4. 生成训练焦点
        training_focuses = self._generate_training_focuses(
            weakness_situations,
            adoption_stats,
            max_focus_items,
        )
        
        # 5. 生成推荐理由
        reasoning = self._generate_reasoning(
            weakness_situations,
            adoption_stats,
        )
        
        # 6. 预估提升
        expected_improvement = self._estimate_improvement(
            weakness_situations,
            adoption_stats,
        )
        
        return CurriculumPlan(
            next_training_plan=training_focuses,
            reasoning=reasoning,
            expected_improvement=expected_improvement,
        )
    
    async def _get_deviation_stats(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> List[Dict]:
        """获取策略偏离统计"""
        query = select(
            StrategyDecision.situation_type,
            StrategyDecision.golden_strategy,
            func.count(StrategyDecision.id).label("total"),
            func.sum(func.cast(StrategyDecision.is_optimal, Integer)).label("optimal"),
            func.avg(StrategyDecision.immediate_score).label("avg_score"),
        ).where(
            StrategyDecision.user_id == user_id
        ).group_by(
            StrategyDecision.situation_type,
            StrategyDecision.golden_strategy,
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "situation_type": row.situation_type,
                "golden_strategy": row.golden_strategy,
                "total_decisions": row.total,
                "optimal_decisions": row.optimal or 0,
                "optimal_rate": (row.optimal or 0) / row.total if row.total > 0 else 0,
                "avg_score": float(row.avg_score or 0),
            }
            for row in rows
        ]
    
    async def _get_adoption_stats(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> Dict:
        """获取采纳效果统计"""
        # 总体采纳率
        total_query = select(
            func.count(AdoptionRecord.id).label("total"),
            func.sum(func.cast(AdoptionRecord.adopted, Integer)).label("adopted"),
            func.sum(func.cast(AdoptionRecord.is_effective, Integer)).label("effective"),
        ).where(
            AdoptionRecord.user_id == user_id
        )
        
        result = await db.execute(total_query)
        row = result.first()
        
        total = row.total or 0
        adopted = row.adopted or 0
        effective = row.effective or 0
        
        # 最有效的技巧
        technique_query = select(
            AdoptionRecord.technique_name,
            func.count(AdoptionRecord.id).label("count"),
            func.avg(AdoptionRecord.effectiveness_score).label("avg_effectiveness"),
        ).where(
            AdoptionRecord.user_id == user_id,
            AdoptionRecord.adopted == True,
        ).group_by(
            AdoptionRecord.technique_name
        ).order_by(
            func.avg(AdoptionRecord.effectiveness_score).desc()
        ).limit(5)
        
        technique_result = await db.execute(technique_query)
        technique_rows = technique_result.all()
        
        most_effective_techniques = [
            {
                "technique": row.technique_name,
                "count": row.count,
                "avg_effectiveness": float(row.avg_effectiveness or 0),
            }
            for row in technique_rows
        ]
        
        return {
            "total_suggestions": total,
            "adopted_count": adopted,
            "effective_count": effective,
            "adoption_rate": adopted / total if total > 0 else 0,
            "effective_adoption_rate": effective / adopted if adopted > 0 else 0,
            "most_effective_techniques": most_effective_techniques,
        }
    
    def _identify_weaknesses(
        self,
        deviation_stats: List[Dict],
    ) -> List[Dict]:
        """识别弱点情境"""
        weaknesses = []
        
        for stat in deviation_stats:
            # 最优率低于 50% 且样本量 >= 3
            if stat["optimal_rate"] < 0.5 and stat["total_decisions"] >= 3:
                weaknesses.append({
                    "situation_type": stat["situation_type"],
                    "golden_strategy": stat["golden_strategy"],
                    "optimal_rate": stat["optimal_rate"],
                    "avg_score": stat["avg_score"],
                    "sample_size": stat["total_decisions"],
                    "gap_severity": 0.5 - stat["optimal_rate"],  # 差距严重程度
                })
        
        # 按差距严重程度排序
        weaknesses.sort(key=lambda x: x["gap_severity"], reverse=True)
        
        return weaknesses
    
    def _generate_training_focuses(
        self,
        weakness_situations: List[Dict],
        adoption_stats: Dict,
        max_items: int,
    ) -> List[TrainingFocus]:
        """生成训练焦点"""
        focuses = []
        
        for i, weakness in enumerate(weakness_situations[:max_items]):
            situation_type = weakness["situation_type"]
            golden_strategy = weakness["golden_strategy"]
            
            # 确定阶段
            stage = self._situation_to_stage(situation_type)
            
            # 获取难度
            difficulty = SITUATION_DIFFICULTY.get(situation_type, "medium")
            
            # 获取 NPC 人设特征
            persona_traits = SITUATION_PERSONA_TRAITS.get(situation_type, ["标准客户"])
            
            # 获取重点 Slot
            focus_slots = STAGE_FOCUS_SLOTS.get(stage, [])
            
            focuses.append(TrainingFocus(
                stage=stage,
                focus_slots=focus_slots,
                focus_strategy=golden_strategy,
                focus_situation=situation_type,
                npc_persona_traits=persona_traits,
                difficulty=difficulty,
                priority=i + 1,
            ))
        
        # 如果没有明确弱点，推荐通用训练
        if not focuses:
            focuses.append(TrainingFocus(
                stage="OBJECTION_HANDLING",
                focus_slots=["objection_type", "objection_resolved"],
                focus_strategy="reframe_value",
                focus_situation=SituationType.PRICE_OBJECTION.value,
                npc_persona_traits=["价格敏感", "精打细算"],
                difficulty="medium",
                priority=1,
            ))
        
        return focuses
    
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
        return stage_mapping.get(situation_type, "OBJECTION_HANDLING")
    
    def _generate_reasoning(
        self,
        weakness_situations: List[Dict],
        adoption_stats: Dict,
    ) -> str:
        """生成推荐理由"""
        # Anti-Cheat: 检测无效刷分 (Inefficient Grinding)
        # 逻辑：单一情境练习超过5次，但最优率仍低于20%，且均分低于5分
        for weakness in weakness_situations:
            if (weakness["sample_size"] > 5 
                and weakness["optimal_rate"] < 0.2 
                and weakness["avg_score"] < 5.0):
                return (
                    f"⚠️ 系统检测到你在【{weakness['situation_type']}】情境下存在高频低效练习（Grinding）。"
                    "建议暂停机械重复，先回顾 SalesBoost 最佳实践手册，或降低难度重新开始。"
                )

        if not weakness_situations:
            return "你的整体表现均衡，建议继续巩固异议处理能力，这是销售成交的关键环节。"
        
        top_weakness = weakness_situations[0]
        situation_cn = self._situation_to_chinese(top_weakness["situation_type"])
        strategy_cn = self._strategy_to_chinese(top_weakness["golden_strategy"])
        optimal_rate = top_weakness["optimal_rate"] * 100
        
        reasoning_parts = [
            f"数据分析显示，你在【{situation_cn}】情境下的最优策略选择率仅为 {optimal_rate:.0f}%，",
            f"而销冠在此情境通常使用【{strategy_cn}】策略。",
        ]
        
        # 添加采纳建议
        if adoption_stats["adoption_rate"] < 0.5:
            reasoning_parts.append(
                f"同时，你对 Coach 建议的采纳率为 {adoption_stats['adoption_rate']*100:.0f}%，"
                "建议更多尝试采纳建议并观察效果。"
            )
        
        if adoption_stats["most_effective_techniques"]:
            top_technique = adoption_stats["most_effective_techniques"][0]
            technique_cn = self._strategy_to_chinese(top_technique["technique"])
            reasoning_parts.append(
                f"历史数据表明，【{technique_cn}】技巧对你最有效，建议在训练中多加练习。"
            )
        
        return "".join(reasoning_parts)
    
    def _estimate_improvement(
        self,
        weakness_situations: List[Dict],
        adoption_stats: Dict,
    ) -> Dict[str, float]:
        """预估提升"""
        improvement = {}
        
        for weakness in weakness_situations[:3]:
            situation = weakness["situation_type"]
            current_rate = weakness["optimal_rate"]
            # 预估提升 10-20%
            expected_rate = min(1.0, current_rate + 0.15)
            improvement[situation] = round(expected_rate - current_rate, 2)
        
        # 整体预估
        if weakness_situations:
            avg_gap = sum(w["gap_severity"] for w in weakness_situations[:3]) / min(3, len(weakness_situations))
            improvement["overall_optimal_rate"] = round(avg_gap * 0.5, 2)  # 预估弥补一半差距
        
        return improvement
    
    def _situation_to_chinese(self, situation_type: str) -> str:
        """情境类型转中文"""
        mapping = {
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
        }
        return mapping.get(situation_type, situation_type)
    
    def _strategy_to_chinese(self, strategy: str) -> str:
        """策略转中文"""
        mapping = {
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
        }
        return mapping.get(strategy, strategy)
    
    async def update_user_profile(
        self,
        db: AsyncSession,
        user_id: str,
        last_session_focus: Optional[Dict] = None,
    ) -> UserStrategyProfile:
        """
        更新用户策略画像
        
        【因果闭环核心】
        UserStrategyProfile 是长期画像，聚合自：
        - StrategyDecision（策略偏离）
        - AdoptionRecord（什么建议有效）
        """
        # ... (Existing logic for stats calculation)
        
        # 获取统计数据
        deviation_stats = await self._get_deviation_stats(db, user_id)
        adoption_stats = await self._get_adoption_stats(db, user_id)
        weakness_situations = self._identify_weaknesses(deviation_stats)
        
        # 计算策略频率
        strategy_freq_query = select(
            StrategyDecision.strategy_chosen,
            func.count(StrategyDecision.id).label("count"),
        ).where(
            StrategyDecision.user_id == user_id
        ).group_by(
            StrategyDecision.strategy_chosen
        )
        
        freq_result = await db.execute(strategy_freq_query)
        freq_rows = freq_result.all()
        strategy_frequency = {row.strategy_chosen: row.count for row in freq_rows}
        
        # 计算各情境最优率
        optimal_rate_by_situation = {
            stat["situation_type"]: stat["optimal_rate"]
            for stat in deviation_stats
        }
        
        # 查找或创建 Profile
        profile_query = select(UserStrategyProfile).where(
            UserStrategyProfile.user_id == user_id
        )
        result = await db.execute(profile_query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserStrategyProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
            )
            db.add(profile)
        
        # P1: Check Curriculum Adherence (Lock Mechanism)
        if last_session_focus and profile.recommended_focus:
            # Check if user followed the recommendation
            recommended = profile.recommended_focus
            
            # Simple check: did the user play the recommended situation?
            # Note: This requires last_session_focus to contain actual played metadata
            played_situation = last_session_focus.get("situation")
            
            if played_situation and recommended.get("situation"):
                if played_situation != recommended.get("situation"):
                    # User ignored recommendation
                    profile.user_override_count = (profile.user_override_count or 0) + 1
                    logger.warning(f"User {user_id} ignored recommendation. Override count: {profile.user_override_count}")
                else:
                    # User followed recommendation, reset counter
                    profile.user_override_count = 0
        
        # 更新字段
        profile.strategy_frequency = strategy_frequency
        profile.optimal_rate_by_situation = optimal_rate_by_situation
        profile.deviation_patterns = [
            {
                "situation": w["situation_type"],
                "golden_strategy": w["golden_strategy"],
                "gap": w["gap_severity"],
            }
            for w in weakness_situations
        ]
        profile.top_weakness_situations = [
            w["situation_type"] for w in weakness_situations[:5]
        ]
        profile.adoption_rate = adoption_stats["adoption_rate"]
        profile.effective_adoption_rate = adoption_stats["effective_adoption_rate"]
        profile.most_effective_techniques = adoption_stats["most_effective_techniques"]
        
        # 生成推荐焦点
        curriculum = await self.generate_curriculum(db, user_id, max_focus_items=1)
        if curriculum.next_training_plan:
            top_focus = curriculum.next_training_plan[0]
            profile.recommended_focus = {
                "stage": top_focus.stage,
                "situation": top_focus.focus_situation,
                "strategy": top_focus.focus_strategy,
                "reasoning": curriculum.reasoning,
            }
            
            # P1: Lock Logic
            # If override count > 2, we enforce a strict lock
            if (profile.user_override_count or 0) >= 2:
                 profile.locked_curriculum = profile.recommended_focus
                 profile.locked_curriculum["reasoning"] = (
                     "⚠️ 检测到多次跳过弱项训练。为保证训练效果，系统已锁定此训练路径。"
                     "请完成此训练以解锁其他内容。"
                 )
            else:
                 profile.locked_curriculum = {}
        
        await db.flush()
        logger.info(f"[CurriculumPlanner] UserStrategyProfile updated: {user_id}")
        
        return profile
    
    async def get_recent_skill_improvements(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        获取最近的能力提升来源
        
        回答：我最近 10 次能力提升来自哪些采纳？
        """
        query = select(
            AdoptionRecord.id,
            AdoptionRecord.suggestion_text,
            AdoptionRecord.technique_name,
            AdoptionRecord.adoption_style,
            AdoptionRecord.skill_delta,
            AdoptionRecord.effectiveness_score,
            AdoptionRecord.situation_type,
            AdoptionRecord.created_at,
        ).where(
            AdoptionRecord.user_id == user_id,
            AdoptionRecord.is_effective == True,
        ).order_by(
            AdoptionRecord.created_at.desc()
        ).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            {
                "id": row.id,
                "suggestion": row.suggestion_text[:100] + "..." if len(row.suggestion_text) > 100 else row.suggestion_text,
                "technique": row.technique_name,
                "adoption_style": row.adoption_style.value if row.adoption_style else "unknown",
                "skill_delta": row.skill_delta,
                "effectiveness_score": row.effectiveness_score,
                "situation": row.situation_type,
                "timestamp": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    
    async def estimate_future_improvement(
        self,
        db: AsyncSession,
        user_id: str,
        training_count: int = 3,
    ) -> Dict[str, float]:
        """
        预估未来训练提升
        
        回答：如果我继续练 N 次，大概能补多少差距？
        """
        # 获取历史有效采纳的平均提升
        avg_improvement_query = select(
            func.avg(AdoptionRecord.effectiveness_score).label("avg_improvement"),
        ).where(
            AdoptionRecord.user_id == user_id,
            AdoptionRecord.is_effective == True,
        )
        
        result = await db.execute(avg_improvement_query)
        row = result.first()
        avg_improvement = float(row.avg_improvement or 0.1)
        
        # 获取当前弱点
        deviation_stats = await self._get_deviation_stats(db, user_id)
        weakness_situations = self._identify_weaknesses(deviation_stats)
        
        estimates = {}
        for weakness in weakness_situations[:3]:
            situation = weakness["situation_type"]
            current_gap = weakness["gap_severity"]
            # 预估每次训练能弥补 avg_improvement 的差距
            estimated_improvement = min(current_gap, avg_improvement * training_count)
            estimates[situation] = round(estimated_improvement, 2)
        
        # 整体预估
        if weakness_situations:
            total_gap = sum(w["gap_severity"] for w in weakness_situations[:3])
            estimates["overall"] = round(min(total_gap, avg_improvement * training_count * 0.8), 2)
        
        return estimates
