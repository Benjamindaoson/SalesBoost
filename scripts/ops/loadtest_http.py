"""Simple HTTP load test for /health endpoint."""
from __future__ import annotations

import asyncio
import os
import time

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
CONCURRENCY = int(os.getenv("CONCURRENCY", "50"))
DURATION = int(os.getenv("DURATION", "30"))


async def worker(client: httpx.AsyncClient, end_time: float, stats: dict) -> None:
    while time.time() < end_time:
        try:
            resp = await client.get(f"{BASE_URL}/health", timeout=5)
            stats["total"] += 1
            if resp.status_code == 200:
                stats["ok"] += 1
            else:
                stats["fail"] += 1
        except Exception:
            stats["fail"] += 1


async def main() -> None:
    end_time = time.time() + DURATION
    stats = {"total": 0, "ok": 0, "fail": 0}
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(worker(client, end_time, stats)) for _ in range(CONCURRENCY)]
        await asyncio.gather(*tasks)

    print("total", stats["total"])
    print("ok", stats["ok"])
    print("fail", stats["fail"])
    if stats["total"]:
        print("success_rate", round(stats["ok"] / stats["total"] * 100, 2))


if __name__ == "__main__":
    asyncio.run(main())
