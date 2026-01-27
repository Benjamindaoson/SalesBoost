from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class BaseAgent:
    """
    Base Agent class for all agents in the system.
    """
    def __init__(self, **kwargs):
        pass

    async def run(self, input_data: Any) -> Any:
        raise NotImplementedError
