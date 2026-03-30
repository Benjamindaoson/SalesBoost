"""Downgrade / Self-healing manager.

A lightweight utility to track and expose active downgrade actions across
critical subsystems. This enables unified observability and automated tests
for self-healing behavior in a large-scale AI-enabled system.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional


class DowngradeManager:
    def __init__(self) -> None:
        # component -> list of (timestamp, reason)
        self._issues: Dict[str, List[str]] = {}

    def register(self, component: str, reason: str) -> None:
        entries = self._issues.setdefault(component, [])
        entries.append(f"{datetime.utcnow().isoformat()} - {reason}")

    def resolve(self, component: Optional[str] = None) -> None:
        if component is None:
            self._issues.clear()
        else:
            self._issues.pop(component, None)

    def clear(self) -> None:
        self._issues.clear()

    def is_degraded(self) -> bool:
        return any(len(v) for v in self._issues.values())

    def get_active_issues(self) -> List[str]:
        items: List[str] = []
        for comp, errs in self._issues.items():
            for e in errs:
                items.append(f"{comp}: {e}")
        return items


downgrade_manager = DowngradeManager()

__all__ = ["downgrade_manager"]
