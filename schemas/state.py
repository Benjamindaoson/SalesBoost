"""
SalesBoost State Definitions
严格的类型定义，遵循 Clean Architecture 原则
"""

from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 兼容性
    class StrEnum(str, Enum):
        pass
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field, validator


class SalesStage(StrEnum):
    """销售流程阶段枚举"""
    OPENING = "OPENING"                    # 开场建立联系
    NEEDS_DISCOVERY = "NEEDS_DISCOVERY"    # 需求发现与挖掘
    PRODUCT_INTRO = "PRODUCT_INTRO"        # 产品介绍与演示
    OBJECTION_HANDLING = "OBJECTION_HANDLING"  # 反对意见处理
    CLOSING = "CLOSING"                    # 结单与成交


class Message(TypedDict):
    """
    消息结构定义
    TypedDict 确保类型安全
    """
    role: str          # "user", "npc", "coach", "system"
    content: str       # 消息内容
    timestamp: str     # ISO格式时间戳
    metadata: dict     # 额外元数据


class GlobalState(TypedDict):
    """
    全局状态定义
    LangGraph 要求使用 TypedDict，但内部字段必须强类型
    """
    messages: List[Message]     # 对话消息历史
    current_stage: SalesStage   # 当前销售阶段
    npc_mood: float            # NPC情绪值 (0.0-1.0)
    turn_count: int            # 对话轮数


class AgentOutput(BaseModel):
    """
    智能体节点输出标准化模型
    禁止返回裸字典，所有节点必须返回此模型
    """
    content: str = Field(..., description="输出内容")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    metadata: dict = Field(default_factory=dict, description="额外元数据")
    suggested_actions: List[str] = Field(default_factory=list, description="建议的后续行动")

    @validator('confidence')
    def validate_confidence(cls, v: float) -> float:
        """验证置信度范围"""
        if not (0.0 <= v <= 1.0):
            raise ValueError('confidence must be between 0.0 and 1.0')
        return v


class FSMTransitionResult(BaseModel):
    """状态机转换结果"""
    from_stage: SalesStage
    to_stage: SalesStage
    reason: str = Field(..., description="转换原因")
    confidence: float = Field(..., ge=0.0, le=1.0, description="转换置信度")


class PromptTemplate(BaseModel):
    """提示词模板模型"""
    name: str
    template: str
    variables: List[str] = Field(default_factory=list)
    description: Optional[str] = None


def create_initial_state() -> GlobalState:
    """
    创建初始状态

    Returns:
        初始化后的全局状态
    """
    return GlobalState(
        messages=[],
        current_stage=SalesStage.OPENING,
        npc_mood=0.5,  # 中性情绪
        turn_count=0
    )


def validate_state(state: GlobalState) -> bool:
    """
    验证状态的有效性

    Args:
        state: 要验证的状态

    Returns:
        状态是否有效
    """
    try:
        # 验证必要字段
        required_fields = ["messages", "current_stage", "npc_mood", "turn_count"]
        for field in required_fields:
            if field not in state:
                return False

        # 验证类型
        if not isinstance(state["messages"], list):
            return False

        if not isinstance(state["current_stage"], SalesStage):
            return False

        if not isinstance(state["npc_mood"], (int, float)):
            return False

        if not isinstance(state["turn_count"], int):
            return False

        # 验证值范围
        if not (0.0 <= state["npc_mood"] <= 1.0):
            return False

        if state["turn_count"] < 0:
            return False

        return True

    except Exception:
        return False


class CoachPayload(BaseModel):
    """
    教练分析输出模式
    强制 LLM 输出结构化数据
    """
    reasoning: str = Field(..., description="详细分析销售员的表现、客户反应和当前阶段的合适性")
    suggestion: str = Field(..., description="具体可执行的销售技巧或话术建议")
    score: int = Field(..., ge=0, le=10, description="0-10之间的整数评分，表示销售员的表现质量")
    techniques: List[str] = Field(default_factory=list, description="建议使用的销售技巧")
    next_action: str = Field(..., description="下一步建议的销售行为")

    class Config:
        """Pydantic 配置"""
        json_encoders = {
            SalesStage: lambda v: v.value
        }