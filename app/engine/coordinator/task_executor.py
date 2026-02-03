"""Background task manager stub."""
from __future__ import annotations

import asyncio
from typing import Dict


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        self._running = True
        try:
            from app.engine.coordinator.lifecycle_job import LifecycleJob
            from core.config import get_settings

            settings = get_settings()
            job = LifecycleJob(interval_seconds=settings.LIFECYCLE_JOB_INTERVAL_SECONDS)
            self.run_task("lifecycle_job", job.run_forever())
        except Exception:
            # Lifecycle job is best-effort; background manager should still run.
            pass

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        self._tasks.clear()

    def run_task(self, task_id: str, coro) -> None:
        """Run a background task and ensure it's cleaned up after completion."""
        if not self._running:
            return
        if task_id in self._tasks and not self._tasks[task_id].done():
            return

        task = asyncio.create_task(coro)
        self._tasks[task_id] = task
        
        # Ensure the task is removed from the dict once finished
        task.add_done_callback(lambda t: self._tasks.pop(task_id, None))

    def get_task_status(self) -> dict:
        return {"running": self._running, "tasks": list(self._tasks.keys())}


background_task_manager = BackgroundTaskManager()
