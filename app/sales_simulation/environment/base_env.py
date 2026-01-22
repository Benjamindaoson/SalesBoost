"""
模拟环境基类
定义标准的 reset/step/done 接口
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import random

from app.sales_simulation.schemas.scenario import SimulationScenario
from app.sales_simulation.schemas.trajectory import StepAction, StepObservation

logger = logging.getLogger(__name__)


class BaseSimulationEnv(ABC):
    """
    模拟环境基类
    
    遵循 Gym-like 接口设计：
    - reset(seed): 重置环境，返回初始观察
    - step(action): 执行动作，返回 (observation, reward, done, info)
    - close(): 关闭环境
    
    核心职责：
    - 管理环境状态
    - 响应 Agent 动作
    - 计算奖励信号
    - 判断终止条件
    """
    
    def __init__(self, scenario: SimulationScenario):
        """
        初始化环境
        
        Args:
            scenario: 模拟场景配置
        """
        self.scenario = scenario
        self.current_step = 0
        self.is_done = False
        self._seed: Optional[int] = None
        
        logger.info(f"Environment initialized: {scenario.id}")
    
    @abstractmethod
    def reset(self, seed: Optional[int] = None) -> StepObservation:
        """
        重置环境到初始状态
        
        Args:
            seed: 随机种子（用于可复现）
            
        Returns:
            初始观察
        """
        pass
    
    @abstractmethod
    def step(self, action: StepAction) -> Tuple[StepObservation, float, bool, Dict[str, Any]]:
        """
        执行一步动作
        
        Args:
            action: Agent 动作
            
        Returns:
            observation: 环境观察
            reward: 奖励信号
            done: 是否结束
            info: 额外信息
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        获取当前环境状态
        
        Returns:
            状态字典
        """
        pass
    
    @abstractmethod
    def is_terminal(self) -> bool:
        """
        判断是否达到终止条件
        
        Returns:
            是否终止
        """
        pass
    
    def close(self) -> None:
        """关闭环境"""
        logger.info(f"Environment closed: {self.scenario.id}")
    
    def set_seed(self, seed: int) -> None:
        """
        设置随机种子
        
        Args:
            seed: 随机种子
        """
        self._seed = seed
        random.seed(seed)
        logger.debug(f"Seed set to {seed}")
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取环境信息
        
        Returns:
            环境信息字典
        """
        return {
            "scenario_id": self.scenario.id,
            "current_step": self.current_step,
            "is_done": self.is_done,
            "seed": self._seed,
        }





