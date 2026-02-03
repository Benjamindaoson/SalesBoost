from typing import Any, Dict, Iterable, List

from app.engine.coordinator.state import CoordinatorState


INTENTS_NEED_TOOLS = {
    "price_inquiry",
    "product_inquiry",
    "benefit_inquiry",
}


def _unique(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def fallback_route(state: CoordinatorState, candidates: Iterable[str]) -> Dict[str, Any]:
    allowed = _unique([c for c in candidates if isinstance(c, str)])
    if not allowed:
        return {
            "target_node": "npc",
            "confidence": 0.0,
            "reason": "no candidates available",
            "source": "fallback",
        }

    reasoning = state.get("reasoning") or {}
    risk = reasoning.get("risk") or {}
    need_human = bool(risk.get("need_human"))
    compliance_risk = bool(risk.get("compliance_risk"))
    need_tools = bool(reasoning.get("need_tools")) or state.get("intent") in INTENTS_NEED_TOOLS

    if need_human and "human" in allowed:
        return {
            "target_node": "human",
            "confidence": 0.4,
            "reason": "risk flagged for human review",
            "source": "fallback",
        }
    if compliance_risk and "compliance" in allowed:
        return {
            "target_node": "compliance",
            "confidence": 0.4,
            "reason": "compliance risk flagged",
            "source": "fallback",
        }
    if need_tools:
        if "tools" in allowed:
            return {
                "target_node": "tools",
                "confidence": 0.4,
                "reason": "heuristic indicates tools are required",
                "source": "fallback",
            }
        if "knowledge" in allowed:
            return {
                "target_node": "knowledge",
                "confidence": 0.4,
                "reason": "heuristic indicates knowledge retrieval is required",
                "source": "fallback",
            }
    if "npc" in allowed:
        return {
            "target_node": "npc",
            "confidence": 0.3,
            "reason": "default to npc reply",
            "source": "fallback",
        }

    return {
        "target_node": allowed[0],
        "confidence": 0.2,
        "reason": "fallback to first available candidate",
        "source": "fallback",
    }
