"""Cost control stub."""
from __future__ import annotations


class _SmartRouter:
    def __init__(self) -> None:
        self.available_models = ["mock"]


class _BudgetManager:
    def __init__(self) -> None:
        self.session_budgets = {}
        self.cost_tracking = {}


class CostOptimizedCaller:
    def __init__(self) -> None:
        self.budget_manager = _BudgetManager()
        self.smart_router = _SmartRouter()


cost_optimized_caller = CostOptimizedCaller()
