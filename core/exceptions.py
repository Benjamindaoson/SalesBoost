"""
SalesBoost Custom Exceptions
自定义异常类，用于错误处理和日志记录
"""

from typing import Any, Dict, Optional
from enum import Enum
try:
    from .error_codes import ERROR_CODE
except Exception:
    # Fallback if import resolves differently in tests
    class ERROR_CODE(Enum):
        UNKNOWN_ERROR = "UNKNOWN_ERROR"


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


def create_error_response(
    error: Exception | None = None,
    *,
    error_code: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
) -> Dict[str, Any]:
    """
    将异常转换为标准错误响应格式。

    兼容两种调用方式：
    - create_error_response(error=Exception)
    - create_error_response(error_code=..., message=..., details=...)
    """
    if isinstance(error, SalesBoostException):
        # Do not leak internal details by default; only include when debugging environments
        # Normalize error code to string value
        code = error.error_code
        if hasattr(code, "value"):
            code = code.value  # type: ignore[assignment]
        include_details = bool(error.details)
        payload = {
            "success": False,
            "error": {
                "code": code if code is not None else ERROR_CODE.UNKNOWN_ERROR.value,  # type: ignore
                "message": error.message,
            },
        }
        if include_details:
            payload["error"]["details"] = error.details
        return payload

    if error is not None:
        payload = {
            "success": False,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": "An unexpected error occurred",
            },
        }
        if __debug__ and details is not None:
            payload["error"]["details"] = {"original_error": str(error), **details}
        elif __debug__:
            payload["error"]["details"] = {"original_error": str(error)}
        return payload

    payload = {
        "success": False,
        "error": {
            "code": error_code or "UNKNOWN_ERROR",
            "message": message or "An unexpected error occurred",
        },
    }
    if __debug__ and details:
        payload["error"]["details"] = details
    return payload


