import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.engine.coordinator.json_utils import extract_json
from app.engine.coordinator.routing_fallback import INTENTS_NEED_TOOLS
from app.engine.coordinator.schemas import RoutingPolicySchema
from app.engine.coordinator.state import CoordinatorState
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.gateway.schemas import AgentType, LatencyMode, ModelCall, RoutingContext
from app.tools.registry import ToolRegistry
from app.observability.performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

ROUTING_SYSTEM_PROMPT = (
    "You are a routing advisor for a sales conversation engine. "
    "Recommend the next node only. Output strictly JSON and nothing else."
)

ROUTING_USER_TEMPLATE = (
    "State:\n"
    "- intent: {intent}\n"
    "- intent_confidence: {confidence}\n"
    "- fsm_stage: {fsm_stage}\n"
    "- core_concern: {core_concern}\n"
    "- strategy: {strategy}\n"
    "- need_tools: {need_tools}\n"
    "- compliance_risk: {compliance_risk}\n"
    "- need_human: {need_human}\n"
    "- recent_tool_calls: {recent_tool_calls}\n\n"
    "Candidates: {candidates}\n\n"
    "Return JSON:\n"
    "{\n"
    '  "target_node": "npc | tools | coach | compliance | human",\n'
    '  "confidence": 0.0,\n'
    '  "reason": "short reason",\n'
    '  "candidates": ["npc", "tools"]\n'
    "}\n"
)


class RoutingAdvisor:
    def __init__(self, model_gateway: ModelGateway, tool_registry: Optional[ToolRegistry] = None) -> None:
        self._gateway = model_gateway
        self._tool_registry = tool_registry

    async def advise(
        self,
        state: CoordinatorState,
        reasoning: Dict[str, Any],
        candidates: Iterable[str],
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        start = time.perf_counter()
        candidate_list = list(candidates)
        message = str(state.get("user_message", "") or "").lower()
        keyword_hits = any(
            kw in message
            for kw in ["年费", "费用", "价格", "多少", "price", "fee", "cost", "pricing"]
        )
        need_tools = (
            bool(reasoning.get("need_tools", False))
            or state.get("intent") in INTENTS_NEED_TOOLS
            or keyword_hits
        )
        if need_tools and candidate_list:
            if "tools" in candidate_list or "knowledge" in candidate_list:
                target = "tools" if "tools" in candidate_list else "knowledge"
                return {
                    "target_node": target,
                    "confidence": 0.72,
                    "reason": "heuristic: tool-needed intent",
                    "candidates": candidate_list,
                }, "heuristic"
        try:
            risk = reasoning.get("risk", {}) if reasoning else {}
            prompt = ROUTING_USER_TEMPLATE.format(
                intent=state.get("intent", ""),
                confidence=state.get("confidence", 0.0),
                fsm_stage=state.get("fsm_state", {}).get("current_stage", ""),
                core_concern=reasoning.get("core_concern", ""),
                strategy=reasoning.get("strategy", ""),
                need_tools=bool(reasoning.get("need_tools", False)),
                compliance_risk=bool(risk.get("compliance_risk", False)),
                need_human=bool(risk.get("need_human", False)),
                recent_tool_calls=bool(state.get("recent_tool_calls", False)),
                candidates=", ".join(candidate_list),
            )
            tools_schema = (
                self._tool_registry.get_tools_schema(agent_type=AgentType.SESSION_DIRECTOR.value)
                if self._tool_registry
                else None
            )
            call = ModelCall(
                prompt=prompt,
                system_prompt=ROUTING_SYSTEM_PROMPT,
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
                raise ValueError("invalid routing response")
            if "candidates" not in parsed:
                parsed["candidates"] = list(candidates)
            validated = RoutingPolicySchema.model_validate(parsed)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            performance_monitor.record("orchestration", "routing", latency_ms, success=True)
            return validated.model_dump(), "llm"
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            performance_monitor.record("orchestration", "routing", latency_ms, success=False)
            logger.warning(f"[RoutingAdvisor] fallback: {exc}")
            return None, "fallback"
