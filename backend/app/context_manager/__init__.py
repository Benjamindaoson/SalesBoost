"""Context management engine for SalesBoost."""
from ..context_manager.engine import ContextManagerEngine


context_manager = ContextManagerEngine()

__all__ = ["ContextManagerEngine", "context_manager"]
