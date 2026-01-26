import logging
import re
from typing import Optional, Tuple

from app.schemas.trace import SecurityEvent

logger = logging.getLogger(__name__)


class SecurityAction:
    PASS = "allow"
    BLOCK = "block"
    REWRITE = "rewrite"
    DOWNGRADE = "downgrade"
    WARN = "warn"


class RuntimeGuard:
    """
    Runtime security guard for input/output checks.
    """

    def __init__(self) -> None:
        self.injection_patterns = [
            (re.compile(r"(ignore|disregard|forget)\s+(all\s+)?(instructions|rules|directions)", re.I), "instruction_bypass"),
            (re.compile(r"system\s+prompt", re.I), "system_prompt_leak"),
            (re.compile(r"you\s+are\s+now\s+a", re.I), "role_jailbreak"),
        ]
        self.forbidden_expressions = [
            (re.compile(r"price\s+too\s+expensive", re.I), "negative_pricing_loop"),
            (re.compile(r"\bi\s+don't\s+know\b", re.I), "low_confidence_refusal"),
        ]
        self.high_risk_keywords = [
            (re.compile(r"refund", re.I), "refund_risk"),
            (re.compile(r"complaint", re.I), "complaint_risk"),
        ]

    def check_input(self, text: str) -> Tuple[str, Optional[SecurityEvent]]:
        """Input guard."""
        for pattern, rule_id in self.injection_patterns:
            if pattern.search(text):
                event = SecurityEvent(
                    event_type="input_injection",
                    action_taken=SecurityAction.BLOCK,
                    rule_id=rule_id,
                    trigger_point="pre_generate",
                    reason=f"Matched pattern: {pattern.pattern}",
                )
                return SecurityAction.BLOCK, event

        for pattern, rule_id in self.high_risk_keywords:
            if pattern.search(text):
                event = SecurityEvent(
                    event_type="high_risk_input",
                    action_taken=SecurityAction.DOWNGRADE,
                    rule_id=rule_id,
                    trigger_point="pre_generate",
                    reason=f"High risk keyword detected: {pattern.pattern}",
                )
                return SecurityAction.DOWNGRADE, event

        return SecurityAction.PASS, None

    def check_output(self, text: str) -> Tuple[str, str, Optional[SecurityEvent]]:
        """Output guard with optional rewrite."""
        modified_text = text
        triggered_event = None

        for pattern, rule_id in self.forbidden_expressions:
            if pattern.search(text):
                modified_text = pattern.sub("Let's discuss the value and outcomes.", modified_text)
                triggered_event = SecurityEvent(
                    event_type="output_forbidden",
                    action_taken=SecurityAction.REWRITE,
                    rule_id=rule_id,
                    trigger_point="post_generate",
                    reason=f"Intercepted forbidden expression: {pattern.pattern}",
                )
                break

        action = SecurityAction.REWRITE if triggered_event else SecurityAction.PASS
        return action, modified_text, triggered_event

    def assess_risk_level(self, context: str) -> int:
        """Estimate risk on a 0-10 scale."""
        risk = 0
        if "price" in context.lower() or "discount" in context.lower():
            risk += 3
        if "complaint" in context.lower() or "angry" in context.lower():
            risk += 5
        return min(risk, 10)


runtime_guard = RuntimeGuard()
