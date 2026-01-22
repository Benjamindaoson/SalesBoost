"""
Model Gateway Schemas
定义模型调用相关的数据结构
"""
from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ProviderType(str, Enum):
    """Provider 类型"""
    OPENAI = "openai"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    MOCK = "mock"  # 用于测试


class AgentType(str, Enum):
    """Agent 类型"""
    SESSION_DIRECTOR = "session_director"
    RETRIEVER = "retriever"
    NPC_GENERATOR = "npc_generator"
    COACH_GENERATOR = "coach_generator"
    EVALUATOR = "evaluator"
    ADOPTION_TRACKER = "adoption_tracker"


class LatencyMode(str, Enum):
    """延迟模式"""
    FAST = "fast"  # 快路径，<3s
    SLOW = "slow"  # 慢路径，5-30s


class RoutingContext(BaseModel):
    """路由上下文"""
    agent_type: AgentType
    turn_importance: float = Field(..., ge=0.0, le=1.0, description="轮次重要性，0-1")
    risk_level: str = Field(default="low", description="风险等级：low/medium/high")
    budget_remaining: float = Field(..., ge=0.0, description="剩余预算（美元）")
    latency_mode: LatencyMode
    retrieval_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="检索置信度")
    turn_number: int = Field(..., ge=1)
    session_id: str


class ModelCall(BaseModel):
    """模型调用记录"""
    call_id: str
    agent_type: AgentType
    provider: ProviderType
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    timestamp: str


class BudgetConfig(BaseModel):
    """预算配置"""
    per_turn_budget: float = Field(default=0.05, description="每轮预算（美元）")
    per_session_budget: float = Field(default=1.0, description="每会话预算（美元）")
    fast_path_budget: float = Field(default=0.02, description="快路径预算（美元）")
    slow_path_budget: float = Field(default=0.03, description="慢路径预算（美元）")


class ModelConfig(BaseModel):
    """模型配置"""
    provider: ProviderType
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: float = 30.0


class RoutingDecision(BaseModel):
    """路由决策"""
    provider: ProviderType
    model: str
    reason: str
    estimated_cost: float
    estimated_latency_ms: float
    fallback_provider: Optional[ProviderType] = None
    fallback_model: Optional[str] = None
