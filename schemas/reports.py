"""
训练报告 Schema
"""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RadarChartData(BaseModel):
    """雷达图数据"""
    labels: List[str] = Field(
        default=["完整性", "相关性", "正确性", "逻辑性", "合规性"],
        description="维度标签",
    )
    values: List[float] = Field(..., description="各维度分数 (0-10)")
    max_value: float = Field(default=10.0, description="最大值")


class StagePerformance(BaseModel):
    """阶段表现"""
    stage: str
    stage_name_cn: str
    turns_spent: int
    avg_score: float
    goal_achieved: bool
    slot_coverage: float
    key_achievements: List[str]
    improvement_areas: List[str]


class TurnDetail(BaseModel):
    """轮次详情"""
    turn_number: int
    user_message: str
    npc_response: str
    stage: str
    scores: Dict[str, float]
    overall_score: float
    coach_suggestion: str
    compliance_passed: bool


class SessionSummary(BaseModel):
    """会话摘要"""
    session_id: str
    user_id: str
    scenario_name: str
    persona_name: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_minutes: int
    total_turns: int
    final_stage: str
    completion_rate: float = Field(..., description="完成度 0-100%")


class StrategyComparison(BaseModel):
    """策略对比 - 你的策略 vs 销冠策略"""
    situation_type: str = Field(..., description="情境类型")
    situation_name_cn: str = Field(..., description="情境中文名")
    your_strategy: str = Field(..., description="你使用的策略")
    champion_strategy: str = Field(..., description="销冠策略")
    is_optimal: bool = Field(..., description="是否最优")
    occurrence_count: int = Field(..., description="出现次数")
    optimal_rate: float = Field(..., description="最优率")


class EffectiveSuggestion(BaseModel):
    """有效建议统计"""
    technique_name: str = Field(..., description="技巧名称")
    technique_name_cn: str = Field(..., description="技巧中文名")
    total_adoptions: int = Field(..., description="总采纳次数")
    effective_adoptions: int = Field(..., description="有效采纳次数")
    effectiveness_rate: float = Field(..., description="有效率")
    avg_skill_improvement: float = Field(..., description="平均能力提升")


class CurriculumRecommendation(BaseModel):
    """训练推荐"""
    focus_situation: str = Field(..., description="重点情境")
    focus_strategy: str = Field(..., description="重点策略")
    difficulty: str = Field(..., description="难度")
    reasoning: str = Field(..., description="推荐理由")
    expected_improvement: float = Field(..., description="预期提升")


class TrainingReport(BaseModel):
    """完整训练报告"""
    # 基本信息
    summary: SessionSummary
    
    # 总体评分
    overall_score: float = Field(..., ge=0.0, le=10.0)
    radar_chart: RadarChartData
    
    # 五维详细评分
    dimension_scores: Dict[str, float]
    dimension_feedback: Dict[str, str]
    
    # 阶段表现
    stage_performances: List[StagePerformance]
    
    # 轮次详情（可选，用于详细回放）
    turn_details: Optional[List[TurnDetail]] = None
    
    # 改进建议
    top_strengths: List[str]
    top_improvements: List[str]
    recommended_focus: str
    
    # ========== 新增：销冠能力复制系统 ==========
    
    # 策略对比：你的策略 vs 销冠策略
    strategy_comparisons: Optional[List[StrategyComparison]] = Field(
        default=None,
        description="策略对比分析"
    )
    overall_optimal_rate: Optional[float] = Field(
        default=None,
        description="整体最优策略选择率"
    )
    
    # 有效建议统计：哪些 Coach 建议最有效
    effective_suggestions: Optional[List[EffectiveSuggestion]] = Field(
        default=None,
        description="最有效的 Coach 建议"
    )
    adoption_rate: Optional[float] = Field(
        default=None,
        description="建议采纳率"
    )
    effective_adoption_rate: Optional[float] = Field(
        default=None,
        description="有效采纳率"
    )
    
    # 训练推荐：下一步应该练什么
    curriculum_recommendations: Optional[List[CurriculumRecommendation]] = Field(
        default=None,
        description="训练推荐"
    )
    
    # ========== 历史对比 ==========
    
    # 与历史对比
    score_vs_average: Optional[float] = None
    score_trend: Optional[List[float]] = None
    
    # 元数据
    generated_at: datetime
    report_version: str = "2.0"
