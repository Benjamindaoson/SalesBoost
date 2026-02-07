"""Simple WebSocket load test for /ws/train."""
from __future__ import annotations

import asyncio
import os
import time
import uuid

import websockets

WS_URL = os.getenv("WS_URL", "ws://localhost:8000/ws/train")
TOKEN = os.getenv("TOKEN")
COURSE_ID = os.getenv("COURSE_ID")
SCENARIO_ID = os.getenv("SCENARIO_ID")
PERSONA_ID = os.getenv("PERSONA_ID")
USER_ID = os.getenv("USER_ID")
CONCURRENCY = int(os.getenv("CONCURRENCY", "20"))
DURATION = int(os.getenv("DURATION", "30"))


def _build_url() -> str:
    if COURSE_ID and SCENARIO_ID and PERSONA_ID and USER_ID:
        return (
            f"{WS_URL}?course_id={COURSE_ID}&scenario_id={SCENARIO_ID}"
            f"&persona_id={PERSONA_ID}&user_id={USER_ID}"
        )
    return f"{WS_URL}?session_id={uuid.uuid4()}&user_id={USER_ID or 'test'}"


async def worker(end_time: float, stats: dict) -> None:
    headers = {}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    while time.time() < end_time:
        try:
            async with websockets.connect(_build_url(), extra_headers=headers) as ws:
                stats["connect"] += 1
                await ws.send('{"type":"ping"}')
                await ws.recv()
                stats["ok"] += 1
        except Exception:
            stats["fail"] += 1


async def main() -> None:
    end_time = time.time() + DURATION
    stats = {"connect": 0, "ok": 0, "fail": 0}
    tasks = [asyncio.create_task(worker(end_time, stats)) for _ in range(CONCURRENCY)]
    await asyncio.gather(*tasks)
    print(stats)


if __name__ == "__main__":
    asyncio.run(main())
