from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Set, Type

from pydantic import BaseModel, ConfigDict

from app.tools.errors import ToolInputError
from app.tools.dependencies import get_dependency_resolver


class ToolInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel] = ToolInputModel
    allowed_agents: Optional[Set[str]] = None
    enabled: bool = True
    is_side_effect_free: bool = True  # Explicit classification for read/write operations

    def __init__(self) -> None:
        if not self.name or not self.description:
            raise ValueError("Tool must define a name and description.")

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.args_schema.model_json_schema()

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._validate(payload)

        # Resolve dependencies
        resolver = get_dependency_resolver()
        resolved_kwargs = await resolver.resolve_dependencies(self._run, data)

        return await self._run(**resolved_kwargs)

    def _validate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            model = self.args_schema.model_validate(payload or {})
        except Exception as exc:
            raise ToolInputError(f"Invalid input for tool {self.name}: {exc}") from exc
        return model.model_dump()

    @abstractmethod
    async def _run(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError
