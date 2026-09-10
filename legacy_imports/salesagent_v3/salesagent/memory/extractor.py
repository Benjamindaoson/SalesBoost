"""Memory Extractor — extracts entities/intents from dialogue into memory."""
from __future__ import annotations

import re
from typing import Any

import structlog

log = structlog.get_logger()


class MemoryExtractor:
    """
    Extracts structured entities from messages and reasoning output
    to store in Adaptive Memory.
    """

    # Simple regex-based extraction patterns (production would use NER model)
    _NAME_PATTERNS = [
        re.compile(r"(?:我叫|我是|您好[，,]?\s*我是)\s*([^\s，,。！？]{2,8})"),
        re.compile(r"my name is ([A-Za-z\s]{2,30})", re.IGNORECASE),
    ]
    _BUDGET_PATTERNS = [
        re.compile(r"预算\s*(?:大概|约|是|有)?\s*([0-9,]+\s*(?:万|千|百|元|K|k)?(?:到|至|-|~)[0-9,]+\s*(?:万|千|百|元|K|k)?)"),
        re.compile(r"budget\s+(?:is|around|of)?\s*\$?([0-9,]+(?:k|K|万)?(?:\s*(?:to|-)\s*\$?[0-9,]+(?:k|K|万)?)?)", re.IGNORECASE),
    ]

    async def extract(
        self,
        message: str,
        reasoning_output: Any | None = None,
        session_id: str = "",
    ) -> list[dict[str, Any]]:
        """
        Extract memory entities from a user message + reasoning context.
        Returns list of {entity_type, key, value, importance_score}.
        """
        entities: list[dict[str, Any]] = []

        # Extract name
        for pattern in self._NAME_PATTERNS:
            m = pattern.search(message)
            if m:
                entities.append({
                    "entity_type": "name",
                    "key": "customer_name",
                    "value": m.group(1).strip(),
                    "importance_score": 0.95,
                })
                break

        # Extract budget
        for pattern in self._BUDGET_PATTERNS:
            m = pattern.search(message)
            if m:
                entities.append({
                    "entity_type": "budget",
                    "key": "budget_range",
                    "value": m.group(1).strip(),
                    "importance_score": 0.85,
                })
                break

        # Extract from reasoning output
        if reasoning_output:
            # Store objection type if non-trivial
            if reasoning_output.customer_signals.objection_type != "none":
                entities.append({
                    "entity_type": "pain_point",
                    "key": "primary_objection",
                    "value": reasoning_output.customer_signals.objection_type,
                    "importance_score": 0.80,
                })

            # Store interest level
            entities.append({
                "entity_type": "emotion",
                "key": "interest_level",
                "value": str(reasoning_output.customer_signals.interest_level),
                "importance_score": 0.60,
            })

            # Store hidden concerns as separate entries
            for i, concern in enumerate(reasoning_output.hidden_concerns[:3]):
                entities.append({
                    "entity_type": "pain_point",
                    "key": f"hidden_concern_{i+1}",
                    "value": concern,
                    "importance_score": 0.70,
                })

        return entities
