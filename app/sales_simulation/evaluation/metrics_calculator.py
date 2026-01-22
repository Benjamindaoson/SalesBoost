"""
指标计算器
计算轨迹评估指标
"""
import logging
from typing import List
import numpy as np

from app.sales_simulation.schemas.trajectory import Trajectory
from app.sales_simulation.schemas.metrics import (
    TrajectoryMetrics,
    ConsistencyMetrics,
    AggregatedMetrics,
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    指标计算器
    
    核心功能：
    - 计算单条轨迹指标
    - 计算多轨迹一致性指标
    - 计算聚合指标
    """
    
    @staticmethod
    def calculate_trajectory_metrics(trajectory: Trajectory) -> TrajectoryMetrics:
        """
        计算单条轨迹指标
        
        Args:
            trajectory: 轨迹对象
            
        Returns:
            轨迹指标
        """
        steps = trajectory.steps
        
        # 计算平均单步得分
        avg_step_score = np.mean([s.step_score for s in steps]) if steps else 0.0
        
        # 计算过程效率
        process_efficiency = 1.0 - (trajectory.total_steps / 20.0)  # 假设最大20步
        process_efficiency = max(0.0, min(1.0, process_efficiency))
        
        # 计算对话质量（基于步骤评分方差）
        step_scores = [s.step_score for s in steps]
        dialogue_quality = 1.0 - (np.std(step_scores) if len(step_scores) > 1 else 0.0)
        dialogue_quality = max(0.0, min(1.0, dialogue_quality))
        
        # 计算合规率
        compliance_count = sum(1 for s in steps if s.observation.compliance_passed)
        compliance_rate = compliance_count / len(steps) if steps else 1.0
        violation_count = len(steps) - compliance_count
        
        # 客户体验指标
        if steps:
            final_obs = steps[-1].observation
            initial_obs = steps[0].observation
            final_customer_mood = final_obs.customer_mood
            mood_improvement = final_obs.customer_mood - initial_obs.customer_mood
        else:
            final_customer_mood = 0.5
            mood_improvement = 0.0
        
        customer_satisfaction = (final_customer_mood + dialogue_quality) / 2.0
        
        # 效率指标
        steps_to_goal = trajectory.total_steps if trajectory.goal_achieved else None
        
        return TrajectoryMetrics(
            trajectory_id=trajectory.id,
            goal_completion_rate=trajectory.final_score,
            goal_achieved=trajectory.goal_achieved,
            avg_step_score=avg_step_score,
            process_efficiency=process_efficiency,
            dialogue_quality=dialogue_quality,
            compliance_rate=compliance_rate,
            violation_count=violation_count,
            final_customer_mood=final_customer_mood,
            mood_improvement=mood_improvement,
            customer_satisfaction=customer_satisfaction,
            total_steps=trajectory.total_steps,
            duration_seconds=trajectory.duration_seconds,
            steps_to_goal=steps_to_goal,
        )
    
    @staticmethod
    def calculate_consistency_metrics(trajectories: List[Trajectory]) -> ConsistencyMetrics:
        """
        计算一致性指标
        
        Args:
            trajectories: 轨迹列表
            
        Returns:
            一致性指标
        """
        if len(trajectories) < 2:
            raise ValueError("Need at least 2 trajectories for consistency metrics")
        
        # 提取指标
        scores = [t.final_score for t in trajectories]
        steps = [t.total_steps for t in trajectories]
        goal_achievements = [1.0 if t.goal_achieved else 0.0 for t in trajectories]
        
        # 计算方差和标准差
        score_std_dev = float(np.std(scores))
        score_mean = float(np.mean(scores))
        score_cv = score_std_dev / score_mean if score_mean > 0 else 0.0
        
        goal_variance = float(np.var(goal_achievements))
        steps_variance = float(np.var(steps))
        
        # 计算策略一致性（简化版：基于步数和得分的一致性）
        strategy_consistency = 1.0 - min(score_cv, 1.0)
        
        # 计算稳定性总分
        stability_score = (
            (1.0 - min(score_cv, 1.0)) * 0.4 +
            (1.0 - min(goal_variance, 1.0)) * 0.3 +
            strategy_consistency * 0.3
        )
        
        return ConsistencyMetrics(
            num_trajectories=len(trajectories),
            goal_achievement_variance=goal_variance,
            score_std_dev=score_std_dev,
            score_coefficient_of_variation=score_cv,
            steps_variance=steps_variance,
            strategy_consistency=strategy_consistency,
            stability_score=stability_score,
        )
    
    @staticmethod
    def calculate_aggregated_metrics(
        run_id: str,
        trajectories: List[Trajectory],
    ) -> AggregatedMetrics:
        """
        计算聚合指标
        
        Args:
            run_id: 运行 ID
            trajectories: 轨迹列表
            
        Returns:
            聚合指标
        """
        if not trajectories:
            raise ValueError("No trajectories to aggregate")
        
        # 成功率
        success_count = sum(1 for t in trajectories if t.goal_achieved)
        success_rate = success_count / len(trajectories)
        
        # 完成率
        completed_count = sum(1 for t in trajectories if t.status == "completed")
        completion_rate = completed_count / len(trajectories)
        
        # 平均指标
        avg_score = float(np.mean([t.final_score for t in trajectories]))
        avg_steps = float(np.mean([t.total_steps for t in trajectories]))
        avg_duration = float(np.mean([t.duration_seconds for t in trajectories]))
        
        # 分布统计
        score_distribution = MetricsCalculator._calculate_distribution(
            [t.final_score for t in trajectories],
            bins=[(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        )
        
        steps_distribution = MetricsCalculator._calculate_distribution(
            [float(t.total_steps) for t in trajectories],
            bins=[(0, 5), (5, 10), (10, 15), (15, 20), (20, 100)]
        )
        
        # 一致性指标
        consistency_metrics = MetricsCalculator.calculate_consistency_metrics(trajectories)
        
        # 整体质量评估
        overall_quality = (
            avg_score * 0.4 +
            success_rate * 0.3 +
            consistency_metrics.stability_score * 0.3
        )
        
        # 推荐建议
        recommendation = MetricsCalculator._generate_recommendation(
            success_rate, avg_score, consistency_metrics.stability_score
        )
        
        return AggregatedMetrics(
            run_id=run_id,
            num_trajectories=len(trajectories),
            success_rate=success_rate,
            completion_rate=completion_rate,
            avg_score=avg_score,
            avg_steps=avg_steps,
            avg_duration=avg_duration,
            score_distribution=score_distribution,
            steps_distribution=steps_distribution,
            consistency_metrics=consistency_metrics,
            overall_quality=overall_quality,
            recommendation=recommendation,
        )
    
    @staticmethod
    def _calculate_distribution(values: List[float], bins: List[tuple]) -> dict:
        """计算分布"""
        distribution = {}
        for low, high in bins:
            count = sum(1 for v in values if low <= v < high)
            key = f"{low}-{high}"
            distribution[key] = count
        return distribution
    
    @staticmethod
    def _generate_recommendation(success_rate: float, avg_score: float, stability: float) -> str:
        """生成推荐建议"""
        if success_rate >= 0.8 and avg_score >= 0.8 and stability >= 0.8:
            return "Agent 表现优秀且稳定，推荐用于生产环境"
        elif success_rate >= 0.6 and avg_score >= 0.7:
            return "Agent 表现良好，建议进一步优化后使用"
        elif success_rate >= 0.4:
            return "Agent 表现一般，需要针对性改进"
        else:
            return "Agent 表现不佳，建议重新训练或调整策略"





