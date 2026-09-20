"""Compatibility boundary for legacy agents.

Legacy V1/V2/V3/A2A agents should migrate behind this adapter instead of being
called directly by new runtime code.
"""

from typing import Any


class LegacyAgentAdapter:
    def __init__(self, agent: Any):
        self.agent = agent

    async def execute(self, *args, **kwargs):
        if hasattr(self.agent, "execute"):
            return await self.agent.execute(*args, **kwargs)
        if hasattr(self.agent, "run"):
            return await self.agent.run(*args, **kwargs)
        raise TypeError("Unsupported legacy agent interface")
