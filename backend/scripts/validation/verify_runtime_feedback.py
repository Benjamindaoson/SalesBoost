# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
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
SESSION_ID = os.getenv("SESSION_ID")


def _build_url() -> str:
    if SESSION_ID:
        user = USER_ID or "test"
        return f"{WS_URL}?session_id={SESSION_ID}&user_id={user}"
    if COURSE_ID and SCENARIO_ID and PERSONA_ID and USER_ID:
        return (
            f"{WS_URL}?course_id={COURSE_ID}&scenario_id={SCENARIO_ID}"
            f"&persona_id={PERSONA_ID}&user_id={USER_ID}"
        )
    raise RuntimeError("Missing SESSION_ID or COURSE_ID/SCENARIO_ID/PERSONA_ID/USER_ID")


async def _recv_until(ws, target_types: set[str], timeout: float = 20.0) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") in target_types:
            return msg
    raise TimeoutError(f"Timed out waiting for {target_types}")


async def _send_message(ws, content: str) -> dict:
    payload = {"type": "message", "content": content, "turn_id": str(uuid.uuid4())}
    await ws.send(json.dumps(payload))
    return await _recv_until(ws, {"turn_result", "error"})


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("TOKEN env var is required")

    url = _build_url()
    headers = {"Authorization": f"Bearer {TOKEN}"}

    print(f"Connecting to {url} ...")
    async with websockets.connect(
        url,
        additional_headers=headers,
        proxy=None,
        open_timeout=20,
    ) as ws:
        init = await _recv_until(ws, {"init", "error"})
        print("Init:", init)

        # Bandit routing test
        print("Sending objection: 太贵了")
        result = await _send_message(ws, "太贵了")
        print("Turn result:", result)
        decision_id = result.get("bandit_decision_id")
        if decision_id:
            feedback = {
                "type": "feedback",
                "feedback_type": "bandit",
                "decision_id": decision_id,
                "reward": 1.0,
                "comment": "Good answer",
            }
            await ws.send(json.dumps(feedback))
            ack = await _recv_until(ws, {"feedback_ack", "error"})
            print("Feedback ack:", ack)
        else:
            print("No bandit decision_id found; feedback skipped.")

        # Tool cache speed test
        question = "白金卡年费多少？"
        print("Sending tool query (first time):", question)
        start = time.time()
        first = await _send_message(ws, question)
        first_latency = (time.time() - start) * 1000
        print("First response:", first)
        print(f"First latency: {first_latency:.2f} ms")

        follow_up = "白金卡年费多少"
        print("Sending tool query (second time):", follow_up)
        start = time.time()
        second = await _send_message(ws, follow_up)
        second_latency = (time.time() - start) * 1000
        print("Second response:", second)
        print(f"Second latency: {second_latency:.2f} ms")
        metadata = second.get("metadata") or {}
        assert metadata.get("cache_hit") is True, f"Expected cache_hit True, got {metadata}"

        print("Done. Check server logs for [Bandit] Reward updated and [ToolCache] Hit.")


if __name__ == "__main__":
    asyncio.run(main())
