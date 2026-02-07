import asyncio
from .errors import TimeoutError

async def run_with_timeout(coro, timeout=5):
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        raise TimeoutError("tool timeout")
