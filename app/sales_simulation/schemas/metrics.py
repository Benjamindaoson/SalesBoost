"""
评估指标 Schema
定义模拟评估的各类指标
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TrajectoryMetrics(BaseModel):
    """单条轨迹的评估指标"""
    trajectory_id: str = Field(..., description="轨迹 ID")
    
    # 目标达成指标
    goal_completion_rate: float = Field(..., ge=0.0, le=1.0, description="目标完成率")
    goal_achieved: bool = Field(..., description="目标是否达成")
    
    # 过程质量指标
    avg_step_score: float = Field(..., ge=0.0, le=1.0, description="平均单步得分")
    process_efficiency: float = Field(..., ge=0.0, le=1.0, description="过程效率")
    dialogue_quality: float = Field(..., ge=0.0, le=1.0, description="对话质量")
    
    # 合规性指标
    compliance_rate: float = Field(..., ge=0.0, le=1.0, description="合规率")
    violation_count: int = Field(default=0, ge=0, description="违规次数")
    
    # 客户体验指标
    final_customer_mood: float = Field(..., ge=0.0, le=1.0, description="最终客户情绪")
    mood_improvement: float = Field(..., ge=-1.0, le=1.0, description="情绪改善度")
    customer_satisfaction: float = Field(..., ge=0.0, le=1.0, description="客户满意度")
    
    # 效率指标
    total_steps: int = Field(..., ge=0, description="总步数")
    duration_seconds: float = Field(..., ge=0.0, description="持续时间")
    steps_to_goal: Optional[int] = Field(None, description="达成目标所需步数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "trajectory_id": "traj_001",
                "goal_completion_rate": 1.0,
                "goal_achieved": True,
                "avg_step_score": 0.82,
                "process_efficiency": 0.75,
                "dialogue_quality": 0.88,
                "compliance_rate": 1.0,
                "violation_count": 0,
                "final_customer_mood": 0.75,
                "mood_improvement": 0.25,
                "customer_satisfaction": 0.80,
                "total_steps": 12,
                "duration_seconds": 245.5,
                "steps_to_goal": 12
            }
        }


class ConsistencyMetrics(BaseModel):
    """一致性指标（多轨迹对比）"""
    num_trajectories: int = Field(..., ge=2, description="轨迹数量")
    
    # 结果一致性
    goal_achievement_variance: float = Field(..., ge=0.0, description="目标达成方差")
    score_std_dev: float = Field(..., ge=0.0, description="得分标准差")
    score_coefficient_of_variation: float = Field(..., ge=0.0, description="得分变异系数")
    
    # 过程一致性
    steps_variance: float = Field(..., ge=0.0, description="步数方差")
    strategy_consistency: float = Field(..., ge=0.0, le=1.0, description="策略一致性")
    
    # 稳定性评分
    stability_score: float = Field(..., ge=0.0, le=1.0, description="稳定性总分")
    
    class Config:
        json_schema_extra = {
            "example": {
                "num_trajectories": 10,
                "goal_achievement_variance": 0.04,
                "score_std_dev": 0.08,
                "score_coefficient_of_variation": 0.10,
                "steps_variance": 2.5,
                "strategy_consistency": 0.85,
                "stability_score": 0.88
            }
        }


class DriftMetrics(BaseModel):
    """漂移指标（检测 Agent 行为漂移）"""
    baseline_trajectory_id: str = Field(..., description="基准轨迹 ID")
    comparison_trajectory_ids: List[str] = Field(..., description="对比轨迹 ID 列表")
    
    # 行为漂移
    action_distribution_drift: float = Field(..., ge=0.0, description="动作分布漂移")
    strategy_drift: float = Field(..., ge=0.0, description="策略漂移")
    
    # 性能漂移
    score_drift: float = Field(..., ge=-1.0, le=1.0, description="得分漂移")
    efficiency_drift: float = Field(..., ge=-1.0, le=1.0, description="效率漂移")
    
    # 漂移严重程度
    drift_severity: str = Field(..., description="漂移严重程度：low/medium/high")
    
    class Config:
        json_schema_extra = {
            "example": {
                "baseline_trajectory_id": "traj_001",
                "comparison_trajectory_ids": ["traj_002", "traj_003"],
                "action_distribution_drift": 0.12,
                "strategy_drift": 0.08,
                "score_drift": -0.05,
                "efficiency_drift": 0.03,
                "drift_severity": "low"
            }
        }


class AggregatedMetrics(BaseModel):
    """聚合指标（运行级别）"""
    run_id: str = Field(..., description="运行 ID")
    num_trajectories: int = Field(..., ge=1, description="轨迹数量")
    
    # 成功率
    success_rate: float = Field(..., ge=0.0, le=1.0, description="成功率")
    completion_rate: float = Field(..., ge=0.0, le=1.0, description="完成率")
    
    # 平均指标
    avg_score: float = Field(..., ge=0.0, le=1.0, description="平均得分")
    avg_steps: float = Field(..., ge=0.0, description="平均步数")
    avg_duration: float = Field(..., ge=0.0, description="平均时长")
    
    # 分布统计
    score_distribution: Dict[str, int] = Field(..., description="得分分布")
    steps_distribution: Dict[str, int] = Field(..., description="步数分布")
    
    # 一致性与稳定性
    consistency_metrics: ConsistencyMetrics = Field(..., description="一致性指标")
    
    # 质量评估
    overall_quality: float = Field(..., ge=0.0, le=1.0, description="整体质量")
    recommendation: str = Field(..., description="推荐建议")
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_001",
                "num_trajectories": 10,
                "success_rate": 0.8,
                "completion_rate": 1.0,
                "avg_score": 0.82,
                "avg_steps": 13.5,
                "avg_duration": 267.3,
                "score_distribution": {"0.7-0.8": 3, "0.8-0.9": 5, "0.9-1.0": 2},
                "overall_quality": 0.85,
                "recommendation": "Agent 表现稳定，建议用于生产环境"
            }
        }




