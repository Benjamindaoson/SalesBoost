"""
Dependency Injection System for Tools

Provides automatic dependency injection for tool execution context.

Features:
- ContextVars-based context propagation
- Automatic injection of Context, SessionID, UserID
- Type-safe dependency declaration
- No manual parameter extraction needed

Usage:
    from app.ai_core.tools.dependencies import get_context, get_session_id

    class MyTool(BaseTool):
        async def _execute(
            self,
            query: str,
            context: Context = Depends(get_context),
            session_id: str = Depends(get_session_id)
        ):
            # context and session_id are automatically injected
            pass
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Optional, Any, Callable, TypeVar
from dataclasses import dataclass
from functools import wraps
import inspect

logger = logging.getLogger(__name__)

# ==================== Context Variables ====================

# Global context variables
current_context: ContextVar[Optional['ExecutionContext']] = ContextVar(
    'current_context',
    default=None
)

current_session_id: ContextVar[Optional[str]] = ContextVar(
    'current_session_id',
    default=None
)

current_user_id: ContextVar[Optional[int]] = ContextVar(
    'current_user_id',
    default=None
)

current_agent_type: ContextVar[Optional[str]] = ContextVar(
    'current_agent_type',
    default=None
)


@dataclass
class ExecutionContext:
    """Tool execution context."""
    session_id: str
    user_id: int
    agent_type: str
    metadata: Dict[str, Any]
    timestamp: str


# ==================== Dependency Functions ====================

def get_context() -> ExecutionContext:
    """Get current execution context."""
    ctx = current_context.get()
    if ctx is None:
        raise RuntimeError("No execution context available")
    return ctx


def get_session_id() -> str:
    """Get current session ID."""
    session_id = current_session_id.get()
    if session_id is None:
        raise RuntimeError("No session ID available")
    return session_id


def get_user_id() -> int:
    """Get current user ID."""
    user_id = current_user_id.get()
    if user_id is None:
        raise RuntimeError("No user ID available")
    return user_id


def get_agent_type() -> str:
    """Get current agent type."""
    agent_type = current_agent_type.get()
    if agent_type is None:
        raise RuntimeError("No agent type available")
    return agent_type


# ==================== Depends Marker ====================

T = TypeVar('T')


class Depends:
    """
    Dependency marker (similar to FastAPI).

    Usage:
        async def my_function(
            context: Context = Depends(get_context),
            session_id: str = Depends(get_session_id)
        ):
            pass
    """

    def __init__(self, dependency: Callable[[], T]):
        self.dependency = dependency

    def __call__(self) -> T:
        return self.dependency()


# ==================== Context Manager ====================

class ExecutionContextManager:
    """
    Manages execution context for tool calls.

    Usage:
        async with ExecutionContextManager.set_context(context):
            # All tool calls within this block have access to context
            result = await tool.run(query="test")
    """

    @staticmethod
    def set_context(
        context: ExecutionContext
    ):
        """Set execution context."""
        class ContextSetter:
            def __enter__(self):
                # Set all context variables
                current_context.set(context)
                current_session_id.set(context.session_id)
                current_user_id.set(context.user_id)
                current_agent_type.set(context.agent_type)
                return context

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear context variables
                current_context.set(None)
                current_session_id.set(None)
                current_user_id.set(None)
                current_agent_type.set(None)

        return ContextSetter()

    @staticmethod
    async def set_context_async(context: ExecutionContext):
        """Async context manager."""
        class AsyncContextSetter:
            async def __aenter__(self):
                current_context.set(context)
                current_session_id.set(context.session_id)
                current_user_id.set(context.user_id)
                current_agent_type.set(context.agent_type)
                return context

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                current_context.set(None)
                current_session_id.set(None)
                current_user_id.set(None)
                current_agent_type.set(None)

        return AsyncContextSetter()


# ==================== Dependency Resolver ====================

class DependencyResolver:
    """
    Resolves dependencies for tool execution.

    Automatically injects dependencies marked with Depends().
    """

    @staticmethod
    def resolve_dependencies(func: Callable) -> Callable:
        """
        Decorator to resolve dependencies.

        Usage:
            @DependencyResolver.resolve_dependencies
            async def my_tool(
                query: str,
                context: Context = Depends(get_context)
            ):
                pass
        """
        sig = inspect.signature(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Resolve dependencies
            resolved_kwargs = kwargs.copy()

            for param_name, param in sig.parameters.items():
                # Skip if already provided
                if param_name in resolved_kwargs:
                    continue

                # Check if parameter has Depends default
                if isinstance(param.default, Depends):
                    try:
                        # Call dependency function
                        resolved_value = param.default()
                        resolved_kwargs[param_name] = resolved_value
                        logger.debug(f"Injected dependency: {param_name}")
                    except Exception as e:
                        logger.error(f"Failed to resolve dependency {param_name}: {e}")
                        raise

            # Call original function with resolved dependencies
            return await func(*args, **resolved_kwargs)

        return wrapper


# ==================== Helper Functions ====================

def create_execution_context(
    session_id: str,
    user_id: int,
    agent_type: str,
    metadata: Optional[Dict] = None,
) -> ExecutionContext:
    """Create execution context."""
    return ExecutionContext(
        session_id=session_id,
        user_id=user_id,
        agent_type=agent_type,
        metadata=metadata or {},
        timestamp=__import__('datetime').datetime.now().isoformat(),
    )
