"""
Dependency Injection System for Tools

This module provides a FastAPI-like dependency injection system for tools,
allowing automatic injection of context, session, and other runtime values
without manual parameter passing.

Features:
- Automatic context injection
- Session management
- Type-safe dependencies
- Lazy evaluation
- Composable dependencies
"""

from __future__ import annotations

import inspect
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional, TypeVar


# Context variables for dependency injection
_current_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("current_context", default=None)
_current_session_id: ContextVar[Optional[str]] = ContextVar("current_session_id", default=None)
_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
_current_agent_type: ContextVar[Optional[str]] = ContextVar("current_agent_type", default=None)

T = TypeVar("T")


class DependencyMarker:
    """
    Marker class for dependencies.

    Similar to FastAPI's Depends, this class marks a parameter as a dependency
    that should be automatically injected at runtime.
    """

    def __init__(self, dependency: Optional[Callable[..., Any]] = None):
        """
        Initialize dependency marker.

        Args:
            dependency: Optional callable that provides the dependency value.
                       If None, the parameter type annotation is used.
        """
        self.dependency = dependency

    def __repr__(self) -> str:
        return f"Depends({self.dependency})"


def Depends(dependency: Optional[Callable[..., Any]] = None) -> Any:
    """
    Mark a parameter as a dependency to be injected.

    Usage:
        class MyTool(BaseTool):
            async def _run(
                self,
                query: str,
                context: Dict = Depends(get_context),
                session_id: str = Depends(get_session_id)
            ):
                # context and session_id are automatically injected
                pass

    Args:
        dependency: Optional callable that provides the dependency value

    Returns:
        DependencyMarker instance
    """
    return DependencyMarker(dependency)


# Built-in dependency providers

def get_context() -> Dict[str, Any]:
    """Get current execution context"""
    context = _current_context.get()
    if context is None:
        return {}
    return context


def get_session_id() -> Optional[str]:
    """Get current session ID"""
    return _current_session_id.get()


def get_user_id() -> Optional[str]:
    """Get current user ID"""
    return _current_user_id.get()


def get_agent_type() -> Optional[str]:
    """Get current agent type"""
    return _current_agent_type.get()


class ExecutionContext:
    """
    Execution context manager for dependency injection.

    This context manager sets up the context variables that will be
    injected into tool dependencies.
    """

    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_type: Optional[str] = None,
    ):
        """
        Initialize execution context.

        Args:
            context: Execution context dictionary
            session_id: Session ID
            user_id: User ID
            agent_type: Agent type
        """
        self.context = context or {}
        self.session_id = session_id
        self.user_id = user_id
        self.agent_type = agent_type

        # Store tokens for cleanup
        self._tokens = []

    def __enter__(self):
        """Enter context and set context variables"""
        self._tokens.append(_current_context.set(self.context))
        if self.session_id:
            self._tokens.append(_current_session_id.set(self.session_id))
        if self.user_id:
            self._tokens.append(_current_user_id.set(self.user_id))
        if self.agent_type:
            self._tokens.append(_current_agent_type.set(self.agent_type))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset context variables"""
        for token in reversed(self._tokens):
            token.var.reset(token)
        self._tokens.clear()

    async def __aenter__(self):
        """Async enter context"""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit context"""
        return self.__exit__(exc_type, exc_val, exc_tb)


class DependencyResolver:
    """
    Resolver for tool dependencies.

    This class analyzes tool methods and resolves their dependencies
    by inspecting type hints and Depends markers.
    """

    def __init__(self):
        """Initialize dependency resolver"""
        self._cache: Dict[Callable, Dict[str, DependencyMarker]] = {}

    def get_dependencies(self, func: Callable) -> Dict[str, DependencyMarker]:
        """
        Extract dependencies from function signature.

        Args:
            func: Function to analyze

        Returns:
            Dictionary mapping parameter names to DependencyMarker instances
        """
        if func in self._cache:
            return self._cache[func]

        dependencies = {}
        signature = inspect.signature(func)

        for param_name, param in signature.parameters.items():
            # Skip self/cls parameters
            if param_name in ("self", "cls"):
                continue

            # Check if parameter has Depends marker as default
            if isinstance(param.default, DependencyMarker):
                dependencies[param_name] = param.default

        self._cache[func] = dependencies
        return dependencies

    async def resolve_dependencies(
        self,
        func: Callable,
        provided_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve all dependencies for a function call.

        Args:
            func: Function to resolve dependencies for
            provided_kwargs: Already provided keyword arguments

        Returns:
            Complete kwargs dictionary with resolved dependencies
        """
        dependencies = self.get_dependencies(func)
        resolved_kwargs = provided_kwargs.copy()

        for param_name, dep_marker in dependencies.items():
            # Skip if already provided
            if param_name in provided_kwargs:
                continue

            # Resolve dependency
            if dep_marker.dependency:
                # Call dependency provider
                if inspect.iscoroutinefunction(dep_marker.dependency):
                    value = await dep_marker.dependency()
                else:
                    value = dep_marker.dependency()
            else:
                # Use default providers based on parameter name
                value = self._resolve_default_dependency(param_name)

            resolved_kwargs[param_name] = value

        return resolved_kwargs

    def _resolve_default_dependency(self, param_name: str) -> Any:
        """
        Resolve dependency using default providers based on parameter name.

        Args:
            param_name: Parameter name

        Returns:
            Resolved dependency value
        """
        # Map common parameter names to providers
        default_providers = {
            "context": get_context,
            "session_id": get_session_id,
            "user_id": get_user_id,
            "agent_type": get_agent_type,
        }

        provider = default_providers.get(param_name)
        if provider:
            return provider()

        # Return None for unknown dependencies
        return None


# Global dependency resolver instance
_resolver = DependencyResolver()


def get_dependency_resolver() -> DependencyResolver:
    """Get global dependency resolver instance"""
    return _resolver
