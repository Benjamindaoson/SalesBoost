"""
SFT 样本生成器
生成监督微调数据
"""
import logging
from typing import List
import uuid

from app.sales_simulation.schemas.trajectory import Trajectory
from app.sales_simulation.schemas.preference import SFTSample

logger = logging.getLogger(__name__)


class SFTGenerator:
    """SFT 样本生成器"""
    
    @staticmethod
    def generate_sft_samples(
        trajectories: List[Trajectory],
        quality_threshold: float = 0.7,
    ) -> List[SFTSample]:
        """
        生成 SFT 样本
        
        Args:
            trajectories: 轨迹列表
            quality_threshold: 质量阈值
            
        Returns:
            SFT 样本列表
        """
        samples = []
        
        # 只选择高质量轨迹
        high_quality_trajs = [t for t in trajectories if t.final_score >= quality_threshold]
        
        for traj in high_quality_trajs:
            for step in traj.steps:
                # 构建上下文
                context = f"阶段: {step.observation.current_stage}\n"
                context += f"客户情绪: {step.observation.customer_mood:.2f}\n"
                context += f"客户响应: {step.observation.customer_response}"
                
                sample = SFTSample(
                    id=str(uuid.uuid4()),
                    trajectory_id=traj.id,
                    step_index=step.step_index,
                    context=context,
                    action=step.action.content,
                    reasoning=step.action.reasoning,
                    quality_score=step.step_score,
                    is_positive_example=step.step_score >= quality_threshold,
                    annotator="auto",
                    annotation_confidence=0.9,
                    tags=["high_quality"] if step.step_score >= 0.8 else [],
                )
                samples.append(sample)
        
        logger.info(f"Generated {len(samples)} SFT samples")
        return samples





