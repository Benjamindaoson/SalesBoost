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

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    def get_task_status(self) -> dict:
        return {"running": self._running, "tasks": list(self._tasks.keys())}


background_task_manager = BackgroundTaskManager()
