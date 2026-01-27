"""Evaluation task stub."""
from __future__ import annotations

import uuid

from app.tasks.store import TASK_STORE, TaskResult, TaskStatus


def run_evaluation_task(session_id: str) -> str:
    task_id = str(uuid.uuid4())
    TASK_STORE[task_id] = TaskResult(task_id=task_id, status=TaskStatus.COMPLETED, result={"session_id": session_id})
    return task_id
