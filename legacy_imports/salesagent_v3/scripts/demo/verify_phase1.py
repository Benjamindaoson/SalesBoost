#!/usr/bin/env python3
"""Current SalesAgent smoke verification.

This replaces the obsolete phase-1 verifier, which referenced removed modules
and old startup commands.
"""

from __future__ import annotations

import asyncio
import sys

import httpx


async def main() -> int:
    try:
        from salesagent.main import app  # noqa: F401
    except Exception as exc:
        print(f"import salesagent.main failed: {exc}")
        return 1

    print("import salesagent.main: ok")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://127.0.0.1:8000/health")
    except httpx.HTTPError as exc:
        print("API server not reachable.")
        print("Start it with: uvicorn salesagent.main:app --host 127.0.0.1 --port 8000")
        print(f"error: {exc}")
        return 2

    if response.status_code != 200:
        print(f"health check failed: HTTP {response.status_code}")
        return 1

    print("GET /health: ok")
    print(response.json())
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
