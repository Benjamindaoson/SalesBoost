"""Background task store stub."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None


TASK_STORE: Dict[str, TaskResult] = {}
