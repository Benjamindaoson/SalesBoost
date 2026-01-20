"""
多智能体运行器
运行多个 Agent 协作完成销售任务
"""
import logging
from typing import Optional

from app.sales_simulation.schemas.scenario import SimulationScenario
from app.sales_simulation.schemas.trajectory import Trajectory
from app.sales_simulation.runners.single_agent_runner import SingleAgentSimulationRunner

logger = logging.getLogger(__name__)


class MultiAgentRunner:
    """
    多智能体运行器
    
    当前实现：简化版，复用 SingleAgentRunner
    未来扩展：
    - 多个 Agent 协作
    - Agent 之间通信
    - 角色分工（Planner / Executor / Reviewer）
    """
    
    def __init__(self, scenario: SimulationScenario):
        """
        初始化运行器
        
        Args:
            scenario: 模拟场景
        """
        self.scenario = scenario
        # 当前简化实现：复用单智能体
        self.single_runner = SingleAgentSimulationRunner(config=None, agent=None, scenario=scenario)
    
    async def run(
        self,
        run_id: str,
        trajectory_index: int,
        seed: Optional[int] = None,
    ) -> Trajectory:
        """
        运行多智能体轨迹
        
        Args:
            run_id: 运行 ID
            trajectory_index: 轨迹索引
            seed: 随机种子
            
        Returns:
            完整轨迹
        """
        logger.info(f"Running multi-agent trajectory {trajectory_index} (simplified mode)")
        
        # 当前简化实现：调用单智能体
        # 未来可扩展为真正的多智能体协作
        trajectory = await self.single_runner.run(run_id, trajectory_index, seed)
        
        # 标记为多智能体模式
        trajectory.agent_config["type"] = "multi"
        
        return trajectory




