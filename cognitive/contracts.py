from typing import Protocol, Dict, Any

class AuditGate(Protocol):
    def check(self, text: str, meta: Dict[str, Any]) -> bool: ...

class ModelCaller(Protocol):
    async def generate(self, prompt: str, context: Dict[str, Any]) -> str: ...

class Tool(Protocol):
    name: str
    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]: ...
