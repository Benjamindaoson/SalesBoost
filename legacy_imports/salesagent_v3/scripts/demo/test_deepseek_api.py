#!/usr/bin/env python3
"""Minimal DeepSeek-compatible chat API smoke test.

Set DEEPSEEK_API_KEY before running:
    python scripts/demo/test_deepseek_api.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx


API_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.xuansuan.top/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v3.2")


async def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Missing DEEPSEEK_API_KEY; skipping live API call.")
        return 2

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "用一句话介绍你自己。"}],
        "temperature": 0.7,
        "max_tokens": 100,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )

    response.raise_for_status()
    data = response.json()
    print(data["choices"][0]["message"]["content"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
