import logging
import time
from typing import Any, Dict, Optional, Tuple

from app.engine.coordinator.json_utils import extract_json
from app.engine.coordinator.schemas import ReasoningSchema
from app.engine.coordinator.state import CoordinatorState
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import AgentType, LatencyMode, ModelCall, RoutingContext
from app.tools.registry import ToolRegistry
from app.observability.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

REASONING_SYSTEM_PROMPT = (
    "You are a sales conversation reasoning engine. "
    "Analyze the user's message and output structured reasoning only. "
    "Do not generate sales scripts. Output strictly JSON and nothing else."
)

REASONING_USER_TEMPLATE = (
    "User message:\n{user_message}\n\n"
    "Known state:\n"
    "- intent: {intent}\n"
    "- intent_confidence: {confidence}\n"
    "- fsm_stage: {fsm_stage}\n"
    "- recent_tool_calls: {recent_tool_calls}\n\n"
    "Tasks:\n"
    "1) Provide up to 3 possible reasons for the user's statement.\n"
    "2) Identify the core concern.\n"
    "3) Recommend a high-level strategy (not scripts).\n"
    "4) Decide if tools are needed.\n"
    "5) Flag compliance risk or need for human review.\n\n"
    "Output JSON schema:\n"
    "{\n"
    '  "analysis": ["reason1", "reason2"],\n'
    '  "core_concern": "short summary",\n'
    '  "strategy": "high level strategy",\n'
    '  "need_tools": true | false,\n'
    '  "why_not_tools": "required when need_tools=false",\n'
    '  "risk": {\n'
    '    "compliance_risk": true | false,\n'
    '    "need_human": true | false,\n'
    '    "risk_reason": "required when any risk is true"\n'
    "  },\n"
    '  "confidence": 0.0\n'
    "}\n"
)


class ReasoningEngine:
    def __init__(self, model_gateway: ModelGateway, tool_registry: Optional[ToolRegistry] = None) -> None:
        self._gateway = model_gateway
        self._tool_registry = tool_registry

    async def analyze(self, state: CoordinatorState) -> Tuple[Dict[str, Any], str]:
        start = time.perf_counter()
        try:
            prompt = REASONING_USER_TEMPLATE.format(
                user_message=state.get("user_message", ""),
                intent=state.get("intent", ""),
                confidence=state.get("confidence", 0.0),
                fsm_stage=state.get("fsm_state", {}).get("current_stage", ""),
                recent_tool_calls=bool(state.get("recent_tool_calls", False)),
            )
            tools_schema = (
                self._tool_registry.get_tools_schema(agent_type=AgentType.SESSION_DIRECTOR.value)
                if self._tool_registry
                else None
            )
            call = ModelCall(
                prompt=prompt,
                system_prompt=REASONING_SYSTEM_PROMPT,
                tools=tools_schema,
                tool_mode="auto",
            )
            ctx = RoutingContext(
                agent_type=AgentType.STRATEGY,
                turn_importance=0.6,
                risk_level="low",
                budget_remaining=5.0,
                latency_mode=LatencyMode.FAST,
                retrieval_confidence=None,
                turn_number=state.get("turn_number", 0),
                session_id=state.get("session_id", "unknown"),
                budget_authorized=True,
            )
            raw = await self._gateway.call(call, ctx)
            parsed = extract_json(raw)
            if not parsed or "tool_calls" in parsed:
                raise ValueError("invalid reasoning response")
            validated = ReasoningSchema.model_validate(parsed)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            performance_monitor.record("orchestration", "reasoning", latency_ms, success=True)
            return validated.model_dump(), "llm"
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            performance_monitor.record("orchestration", "reasoning", latency_ms, success=False)
            logger.warning(f"[ReasoningEngine] fallback: {exc}")
            return self._fallback_reasoning(state), "fallback"

    def _fallback_reasoning(self, state: CoordinatorState) -> Dict[str, Any]:
        intent = state.get("intent", "")
        confidence = float(state.get("confidence", 0.0))
        need_tools = intent in {"price_inquiry", "product_inquiry", "benefit_inquiry"}
        if need_tools:
            why_not_tools = ""
        else:
            why_not_tools = "sufficient context to respond without tools"
        reasoning = ReasoningSchema(
            analysis=["insufficient signal, defaulting to clarification"],
            core_concern="clarify requirements",
            strategy="ask for clarification and confirm needs",
            need_tools=need_tools,
            why_not_tools=why_not_tools,
            risk={"compliance_risk": False, "need_human": False, "risk_reason": ""},
            confidence=min(0.5, confidence),
        )
        return reasoning.model_dump()
