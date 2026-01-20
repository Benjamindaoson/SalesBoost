"""
SalesBoost Custom Exceptions
自定义异常类，用于错误处理和日志记录
"""

from typing import Optional, Dict, Any


class SalesBoostException(Exception):
    """SalesBoost 基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(SalesBoostException):
    """配置相关错误"""
    pass


class ValidationError(SalesBoostException):
    """数据验证错误"""
    pass


class WebSocketError(SalesBoostException):
    """WebSocket 通信错误"""
    pass


class FSMError(SalesBoostException):
    """状态机逻辑错误"""
    pass


class AgentError(SalesBoostException):
    """智能体执行错误"""
    pass


class PromptError(SalesBoostException):
    """提示词相关错误"""
    pass


class SessionError(SalesBoostException):
    """会话管理错误"""
    pass


def create_error_response(error: Exception) -> Dict[str, Any]:
    """
    将异常转换为标准错误响应格式

    Args:
        error: 异常对象

    Returns:
        标准化的错误响应字典
    """
    if isinstance(error, SalesBoostException):
        return {
            "success": False,
            "error": {
                "code": error.error_code,
                "message": error.message,
                "details": error.details
            }
        }

    # 处理未知异常
    return {
        "success": False,
        "error": {
            "code": "UNKNOWN_ERROR",
            "message": "An unexpected error occurred",
            "details": {"original_error": str(error)}
        }
    }


