"""Compliance agent stub."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.config import get_settings


@dataclass
class RiskFlag:
    risk_type: str


@dataclass
class ComplianceResult:
    risk_level: str
    risk_flags: List[RiskFlag]
    safe_rewrite: str


class ComplianceAgent:
    async def check(self, message: str, stage=None, context=None) -> ComplianceResult:
        settings = get_settings()
        risk_flags: List[RiskFlag] = []
        for word in settings.COMPLIANCE_INTERCEPT_WORDS:
            if word.lower() in (message or "").lower():
                risk_flags.append(RiskFlag(risk_type=word))
        if risk_flags:
            return ComplianceResult(risk_level="WARN", risk_flags=risk_flags, safe_rewrite="Please use compliant language.")
        return ComplianceResult(risk_level="OK", risk_flags=[], safe_rewrite="")
