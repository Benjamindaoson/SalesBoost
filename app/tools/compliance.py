from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agents.roles.compliance_agent import ComplianceAgent
from app.infra.gateway.schemas import AgentType
from app.tools.base import BaseTool, ToolInputModel


class ComplianceCheckInput(ToolInputModel):
    text: str = Field(..., min_length=1, description="Text to scan")
    stage: Optional[str] = Field(None, description="Optional sales stage context")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Session context")


class ComplianceCheckTool(BaseTool):
    name = "compliance_check"
    description = "Check text for compliance risks and provide safe rewrite guidance."
    args_schema = ComplianceCheckInput
    allowed_agents = {
        AgentType.COMPLIANCE.value,
        AgentType.SESSION_DIRECTOR.value,
    }

    def __init__(self) -> None:
        self._agent = ComplianceAgent()
        super().__init__()

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = await self._agent.check(
            message=payload["text"],
            stage=payload.get("stage"),
            context=payload.get("context"),
        )
        return {
            "risk_level": result.risk_level,
            "risk_flags": [
                {"risk_type": flag.risk_type, "severity": flag.severity}
                for flag in result.risk_flags
            ],
            "safe_rewrite": result.safe_rewrite,
        }
