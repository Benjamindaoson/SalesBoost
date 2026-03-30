from typing import Any

class BaseAgent:
    """
    Base Agent class for all agents in the system.
    """
    def __init__(self, **kwargs):
        pass

    async def run(self, input_data: Any) -> Any:
        raise NotImplementedError
