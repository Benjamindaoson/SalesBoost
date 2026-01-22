"""
轨迹分析器
分析轨迹模式和异常
"""
import logging
from typing import List, Dict, Any

from app.sales_simulation.schemas.trajectory import Trajectory

logger = logging.getLogger(__name__)


class TrajectoryAnalyzer:
    """轨迹分析器"""
    
    @staticmethod
    def analyze_patterns(trajectories: List[Trajectory]) -> Dict[str, Any]:
        """分析轨迹模式"""
        if not trajectories:
            return {}
        
        # 分析成功轨迹的共同模式
        successful = [t for t in trajectories if t.goal_achieved]
        failed = [t for t in trajectories if not t.goal_achieved]
        
        return {
            "total_trajectories": len(trajectories),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "success_rate": len(successful) / len(trajectories),
            "avg_steps_success": sum(t.total_steps for t in successful) / len(successful) if successful else 0,
            "avg_steps_failed": sum(t.total_steps for t in failed) / len(failed) if failed else 0,
        }
    
    @staticmethod
    def detect_anomalies(trajectory: Trajectory) -> List[str]:
        """检测异常"""
        anomalies = []
        
        if trajectory.total_steps < 3:
            anomalies.append("轨迹过短")
        
        if trajectory.total_steps > 25:
            anomalies.append("轨迹过长")
        
        if trajectory.final_score < 0.3:
            anomalies.append("得分过低")
        
        return anomalies





