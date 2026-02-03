from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Union

from app.infra.gateway.schemas import AgentType
from app.tools.base import BaseTool
from app.tools.errors import ToolNotFoundError, ToolPermissionError

AgentRef = Union[str, AgentType]


def _normalize_agent(agent: Optional[AgentRef]) -> Optional[str]:
    if agent is None:
        return None
    if isinstance(agent, AgentType):
        return agent.value.lower()
    return str(agent).lower()


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def register_many(self, tools: Iterable[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def enable_tool(self, name: str) -> None:
        tool = self.get_tool(name, require_permission=False)
        tool.enabled = True

    def disable_tool(self, name: str) -> None:
        tool = self.get_tool(name, require_permission=False)
        tool.enabled = False

    def list_tools(
        self,
        agent_type: Optional[AgentRef] = None,
        include_disabled: bool = False,
    ) -> List[BaseTool]:
        tools = list(self._tools.values())
        if not include_disabled:
            tools = [tool for tool in tools if tool.enabled]
        if agent_type is None:
            return tools
        return [tool for tool in tools if self._is_allowed(tool, agent_type)]

    def get_tools_schema(
        self,
        agent_type: Optional[AgentRef] = None,
        include_disabled: bool = False,
    ) -> List[Dict[str, object]]:
        return [tool.schema() for tool in self.list_tools(agent_type, include_disabled)]

    def get_tool(
        self,
        name: str,
        agent_type: Optional[AgentRef] = None,
        require_permission: bool = True,
    ) -> BaseTool:
        tool = self._tools.get(name)
        if not tool:
            raise ToolNotFoundError(f"Tool not found: {name}")
        if not tool.enabled:
            raise ToolNotFoundError(f"Tool disabled: {name}")
        if require_permission and not self._is_allowed(tool, agent_type):
            raise ToolPermissionError(f"Tool not permitted: {name}")
        return tool

    def _is_allowed(self, tool: BaseTool, agent_type: Optional[AgentRef]) -> bool:
        if not tool.allowed_agents:
            return True
        normalized = _normalize_agent(agent_type)
        if normalized is None:
            return False
        allowed = {_normalize_agent(agent) for agent in tool.allowed_agents}
        if "*" in allowed or "system" in allowed:
            return True
        return normalized in allowed


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    from app.tools.compliance import ComplianceCheckTool
    from app.tools.profile_reader import ProfileReaderTool
    from app.tools.retriever import KnowledgeRetrieverTool
    from app.tools.stage_classifier import StageClassifierTool
    from app.tools.price_calculator import PriceCalculatorTool
    from app.tools.crm_integration import CRMIntegrationTool
    from app.tools.outreach.sms_tool import SMSOutreachTool
    from app.tools.competitor_analysis import CompetitorAnalysisTool

    # P0 Tools - Core functionality
    registry.register(KnowledgeRetrieverTool())
    registry.register(ProfileReaderTool())
    registry.register(ComplianceCheckTool())

    # P1 Tools - Enhanced functionality
    registry.register(PriceCalculatorTool())
    registry.register(StageClassifierTool())

    # P1.1 Tools - New tools (Week 2)
    registry.register(CRMIntegrationTool())
    registry.register(SMSOutreachTool())
    registry.register(CompetitorAnalysisTool())

    return registry
