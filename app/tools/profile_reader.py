from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field

from app.context_manager.memory import ContextMemoryStore
from app.infra.gateway.schemas import AgentType
from app.tools.base import BaseTool, ToolInputModel


class ProfileReaderInput(ToolInputModel):
    user_id: str = Field(..., min_length=1, description="User identifier")
    field: Optional[str] = Field(None, description="Specific profile field to fetch")


class ProfileReaderTool(BaseTool):
    name = "profile_reader"
    description = "Read structured customer profile data from long-term memory."
    args_schema = ProfileReaderInput
    allowed_agents = {
        AgentType.COACH.value,
        AgentType.SESSION_DIRECTOR.value,
    }

    def __init__(self, memory_store: Optional[ContextMemoryStore] = None) -> None:
        self._memory = memory_store or ContextMemoryStore()
        super().__init__()

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_id = payload["user_id"]
        field = payload.get("field")
        profile = await self._memory.read_json(f"ctx:s2:{user_id}")
        if field:
            value = profile.get(field)
            return {
                "user_id": user_id,
                "field": field,
                "value": value,
                "found": value is not None,
                "profile": {},
            }
        return {
            "user_id": user_id,
            "profile": profile or {},
            "found": bool(profile),
        }
