"""Guard Rewriter — lightweight model rewriting of flagged sentences."""
from __future__ import annotations

import structlog

from salesagent.core.constants import GuardRiskType

log = structlog.get_logger()

_SAFE_FALLBACKS: dict[GuardRiskType, str] = {
    GuardRiskType.FALSE_PROMISE: "我们会努力确保您获得最好的体验，并在整个合作过程中全力支持您。",
    GuardRiskType.PRICE_LEAK: "关于价格，我们会根据您的具体需求给出最合适的方案，可以约个时间详细讨论。",
    GuardRiskType.COMPETITOR_DEFAMATION: "我们专注于为您提供最适合您场景的解决方案，欢迎与其他方案做对比评估。",
    GuardRiskType.SENSITIVE_INFO: "这部分信息我需要内部确认后再给您准确答复，请稍等。",
    GuardRiskType.UNAUTHORIZED_COMMITMENT: "关于这个问题，我需要和相关团队确认具体的服务条款，确保给您最准确的承诺。",
}


class GuardRewriter:
    """
    Rewrites a flagged sentence using a two-tier strategy:
    1. Low severity (< 0.3): Use template replacement (0ms LLM call)
    2. Medium/High severity (≥ 0.3): Use lightweight LLM rewrite (≤ 100ms)

    Falls back to pre-defined safe replacements if the model call fails.
    """

    def __init__(self, gateway: object) -> None:
        self.gateway = gateway

    async def rewrite(
        self, flagged_sentence: str, risk_type: GuardRiskType, session_id: str = "", severity: float = 0.5
    ) -> str:
        """
        Rewrite flagged sentence based on severity.

        Args:
            flagged_sentence: The sentence that triggered the rule
            risk_type: Type of compliance violation
            session_id: Session identifier for logging
            severity: Risk severity score [0.0, 1.0]
        """
        # Low severity: use template replacement (fast path)
        if severity < 0.3:
            log.debug(
                "Guard: using template replacement (low severity)",
                risk_type=risk_type.value,
                severity=severity,
            )
            return _SAFE_FALLBACKS.get(risk_type, "")

        # Medium/High severity: use LLM rewrite
        try:
            from salesagent.reasoning.prompts import GUARD_REWRITE_PROMPT

            prompt = GUARD_REWRITE_PROMPT.format(
                risk_type=risk_type.value,
                flagged_sentence=flagged_sentence,
            )

            log.debug(
                "Guard: using LLM rewrite (medium/high severity)",
                risk_type=risk_type.value,
                severity=severity,
            )

            result = await self.gateway.complete(  # type: ignore[attr-defined]
                task="guard_rewrite",
                system="You are a sales compliance expert. Rewrite flagged sentences to remove violations while keeping a natural, helpful tone.",
                user=prompt,
                session_id=session_id,
            )

            # Validate the rewrite doesn't still trigger violations
            from salesagent.guard.rules import check_sentence
            if check_sentence(result.strip()):
                log.warning("Guard rewrite still violates rules, using safe fallback")
                return _SAFE_FALLBACKS.get(risk_type, "")
            return result.strip()

        except Exception as exc:
            log.warning("Guard rewriter failed, using safe fallback", risk_type=risk_type.value, error=str(exc))
            return _SAFE_FALLBACKS.get(risk_type, "")
