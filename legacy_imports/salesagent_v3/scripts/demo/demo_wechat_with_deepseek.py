#!/usr/bin/env python3
"""Tiny WeChat-style sales conversation demo backed by a DeepSeek-compatible API.

Set DEEPSEEK_API_KEY before running:
    python scripts/demo/demo_wechat_with_deepseek.py
"""

from __future__ import annotations

import asyncio
import os

import httpx


API_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.xuansuan.top/v1")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v3.2")


class ChatClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def reply(self, history: list[dict[str, str]], message: str) -> str:
        messages = [
            {
                "role": "system",
                "content": "你是专业销售顾问。回复要简短、自然、先理解需求再推进下一步。",
            },
            *history,
            {"role": "user", "content": message},
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 300},
            )

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Missing DEEPSEEK_API_KEY; skipping live API call.")
        return 2

    client = ChatClient(api_key)
    history: list[dict[str, str]] = []

    for user_message in ["你好", "我想了解你们的护肤品", "我是干性皮肤，有推荐吗？"]:
        print(f"客户: {user_message}")
        assistant_message = await client.reply(history, user_message)
        print(f"销售顾问: {assistant_message}\n")
        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message},
            ]
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
