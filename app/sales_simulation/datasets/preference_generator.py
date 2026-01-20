"""
偏好对生成器
生成 DPO 训练数据
"""
import logging
from typing import List, Optional
import uuid

from app.sales_simulation.schemas.trajectory import Trajectory
from app.sales_simulation.schemas.preference import PreferencePair

logger = logging.getLogger(__name__)


class PreferenceGenerator:
    """偏好对生成器"""
    
    @staticmethod
    def generate_preference_pairs(
        trajectories: List[Trajectory],
        run_id: str,
        scenario_id: str,
        min_score_delta: float = 0.1,
    ) -> List[PreferencePair]:
        """
        生成偏好对
        
        Args:
            trajectories: 轨迹列表
            run_id: 运行 ID
            scenario_id: 场景 ID
            min_score_delta: 最小得分差异
            
        Returns:
            偏好对列表
        """
        pairs = []
        
        # 按得分排序
        sorted_trajs = sorted(trajectories, key=lambda t: t.final_score, reverse=True)
        
        # 生成偏好对：高分 vs 低分
        for i in range(len(sorted_trajs) - 1):
            chosen = sorted_trajs[i]
            rejected = sorted_trajs[i + 1]
            
            score_delta = chosen.final_score - rejected.final_score
            
            if score_delta >= min_score_delta:
                # 提取关键步骤作为对比
                if chosen.steps and rejected.steps:
                    pair = PreferencePair(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        scenario_id=scenario_id,
                        chosen_trajectory_id=chosen.id,
                        rejected_trajectory_id=rejected.id,
                        context="销售对话场景",
                        chosen_response=chosen.steps[0].action.content if chosen.steps else "",
                        rejected_response=rejected.steps[0].action.content if rejected.steps else "",
                        score_delta=score_delta,
                        quality_delta=score_delta,
                        preference_reason=f"更优轨迹得分更高（{chosen.final_score:.2f} vs {rejected.final_score:.2f}）",
                        preference_dimensions={
                            "overall_quality": score_delta,
                        },
                    )
                    pairs.append(pair)
        
        logger.info(f"Generated {len(pairs)} preference pairs")
        return pairs




