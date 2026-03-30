"""
SalesBoost WebSocket Communication Protocol
严格的通信协议定义，遵循 Clean Architecture
"""

from enum import Enum

try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 兼容性
    class StrEnum(str, Enum):
        pass
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, validator


class ChannelType(StrEnum):
    """消息通道类型枚举"""
    NPC = "NPC"          # NPC（模拟客户）消息
    COACH = "COACH"      # 教练建议消息
    SYSTEM = "SYSTEM"    # 系统消息


class WebSocketMessage(BaseModel):
    """
    WebSocket 消息基础模型
    所有消息都必须包含 channel 字段
    """
    channel: ChannelType = Field(..., description="消息通道类型")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="消息时间戳")
    session_id: str = Field(..., description="会话ID")
    data: Optional[Dict[str, Any]] = Field(default=None, description="额外数据")

    class Config:
        """Pydantic 配置"""
        use_enum_values = True
        json_encoders = {
            ChannelType: lambda v: v.value
        }


class SystemMessage(WebSocketMessage):
    """系统消息"""
    channel: ChannelType = Field(default=ChannelType.SYSTEM, const=True)

    class Config:
        """系统消息特殊配置"""
        fields = {'channel': {'const': True}}


class NPCMessage(WebSocketMessage):
    """NPC消息"""
    channel: ChannelType = Field(default=ChannelType.NPC, const=True)
    mood_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="NPC情绪分数")

    class Config:
        """NPC消息特殊配置"""
        fields = {'channel': {'const': True}}


class CoachMessage(WebSocketMessage):
    """教练消息"""
    channel: ChannelType = Field(default=ChannelType.COACH, const=True)
    priority: str = Field(default="medium", description="建议优先级")
    techniques: list[str] = Field(default_factory=list, description="建议使用的技巧")

    @validator('priority')
    def validate_priority(cls, v: str) -> str:
        """验证优先级"""
        valid_priorities = ["low", "medium", "high", "urgent"]
        if v not in valid_priorities:
            raise ValueError(f'priority must be one of {valid_priorities}')
        return v

    class Config:
        """教练消息特殊配置"""
        fields = {'channel': {'const': True}}


class UserMessage(BaseModel):
    """用户输入消息"""
    content: str = Field(..., description="用户输入内容")
    timestamp: Optional[str] = Field(None, description="消息时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class ErrorMessage(WebSocketMessage):
    """错误消息"""
    channel: ChannelType = Field(default=ChannelType.SYSTEM, const=True)
    error_code: str = Field(..., description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")

    class Config:
        """错误消息特殊配置"""
        fields = {'channel': {'const': True}}


class SessionStateMessage(WebSocketMessage):
    """会话状态消息"""
    channel: ChannelType = Field(default=ChannelType.SYSTEM, const=True)
    current_stage: str = Field(..., description="当前销售阶段")
    npc_mood: float = Field(..., ge=0.0, le=1.0, description="NPC情绪值")
    turn_count: int = Field(..., ge=0, description="对话轮数")

    class Config:
        """会话状态消息特殊配置"""
        fields = {'channel': {'const': True}}


# 消息类型联合类型
MessageUnion = Union[
    WebSocketMessage,
    SystemMessage,
    NPCMessage,
    CoachMessage,
    ErrorMessage,
    SessionStateMessage
]


# 消息类型映射，方便反序列化
MESSAGE_TYPE_MAP = {
    ChannelType.NPC: NPCMessage,
    ChannelType.COACH: CoachMessage,
    ChannelType.SYSTEM: SystemMessage,
}


def parse_websocket_message(data: Dict[str, Any]) -> MessageUnion:
    """
    解析 WebSocket 消息数据

    Args:
        data: 消息数据字典

    Returns:
        解析后的消息对象

    Raises:
        ValueError: 当消息格式无效时
    """
    try:
        channel_str = data.get("channel")
        if not channel_str:
            raise ValueError("Missing required field: 'channel'")

        channel = ChannelType(channel_str)
        message_class = MESSAGE_TYPE_MAP.get(channel, WebSocketMessage)

        # 处理特殊消息类型
        if channel == ChannelType.SYSTEM:
            # 检查是否为错误消息或会话状态消息
            if "error_code" in data:
                message_class = ErrorMessage
            elif "current_stage" in data:
                message_class = SessionStateMessage
            else:
                message_class = SystemMessage

        return message_class(**data)

    except Exception as e:
        raise ValueError(f"Invalid message format: {e}")


def create_system_message(
    content: str,
    session_id: str,
    data: Optional[Dict[str, Any]] = None
) -> SystemMessage:
    """创建系统消息的工厂函数"""
    import datetime
    return SystemMessage(
        content=content,
        timestamp=datetime.datetime.utcnow().isoformat(),
        session_id=session_id,
        data=data
    )


def create_error_message(
    error_code: str,
    message: str,
    session_id: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorMessage:
    """创建错误消息的工厂函数"""
    import datetime
    return ErrorMessage(
        content=message,
        timestamp=datetime.datetime.utcnow().isoformat(),
        session_id=session_id,
        error_code=error_code,
        error_details=details
    )