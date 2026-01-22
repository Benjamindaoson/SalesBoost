"""
模拟平台配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class SimulationConfig(BaseSettings):
    """模拟平台配置"""
    
    # 场景目录
    SCENARIOS_DIR: Optional[str] = None
    
    # 默认配置
    DEFAULT_MAX_TURNS: int = 20
    DEFAULT_TIMEOUT_SECONDS: int = 600
    DEFAULT_NUM_TRAJECTORIES: int = 5
    DEFAULT_SEED: int = 42
    
    # Agent 配置
    DEFAULT_AGENT_MODEL: str = "gpt-4"
    DEFAULT_AGENT_TEMPERATURE: float = 0.2
    DEFAULT_AGENT_MAX_TOKENS: int = 2000
    
    # 评估配置
    QUALITY_THRESHOLD: float = 0.7
    MIN_SCORE_DELTA: float = 0.1
    
    # 数据导出
    EXPORT_DIR: str = "exports"
    
    class Config:
        env_prefix = "SALES_SIM_"
        case_sensitive = True


# 全局配置实例
simulation_config = SimulationConfig()





