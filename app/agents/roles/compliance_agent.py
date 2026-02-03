"""Compliance agent."""
from __future__ import annotations

import re
import uuid
import random
from dataclasses import dataclass
from typing import List, Optional

from core.config import get_settings
from core.database import get_db_session
from models.memory_service_models import MemoryStrategyUnit
from sqlalchemy import select
from app.infra.events.bus import bus
from app.infra.events.schemas import AuditEventPayload, EventType


@dataclass
class RiskFlag:
    risk_type: str
    severity: str = "medium"


@dataclass
class ComplianceResult:
    risk_level: str
    risk_flags: List[RiskFlag]
    safe_rewrite: str


class ComplianceAgent:
    async def _get_dynamic_replacement(self, risk_flags: List[RiskFlag], context: Optional[dict]) -> str:
        tenant_id = (context or {}).get("tenant_id", "default")
        risk_types = [f.risk_type for f in risk_flags]
        
        async for db in get_db_session():
            try:
                # Search for strategy unit with type 'compliance_replacement' 
                stmt = select(MemoryStrategyUnit).where(
                    MemoryStrategyUnit.tenant_id == tenant_id,
                    MemoryStrategyUnit.type == "compliance_replacement",
                    MemoryStrategyUnit.is_enabled == True
                )
                result = await db.execute(stmt)
                strategies = result.scalars().all()
                
                for strategy in strategies:
                    # Check if any risk type matches the trigger condition keywords
                    trigger_cond = str(strategy.trigger_condition).lower()
                    if any(rt.lower() in trigger_cond for rt in risk_types):
                        if strategy.scripts:
                            return random.choice(strategy.scripts)
                
                # Fallback to general compliance replacement if no specific match
                for strategy in strategies:
                    if strategy.trigger_condition == {} and strategy.scripts:
                        return random.choice(strategy.scripts)
                        
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to fetch dynamic compliance replacement: {e}")
            finally:
                break
        
        return "抱歉，由于涉及合规风险，该内容已被拦截。请参考合规指引继续交流。"

    async def check(self, message: str, stage=None, context=None) -> ComplianceResult:
        settings = get_settings()
        text = (message or "").strip()
        text_lower = text.lower()
        risk_flags: List[RiskFlag] = []

        for word in settings.COMPLIANCE_INTERCEPT_WORDS:
            if word.lower() in text_lower:
                risk_flags.append(RiskFlag(risk_type=word, severity="medium"))

        for pattern in settings.SECURITY_INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                risk_flags.append(RiskFlag(risk_type="prompt_injection", severity="high"))

        if re.search(r"\b\d{11}\b", text):
            risk_flags.append(RiskFlag(risk_type="pii_phone", severity="medium"))
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            risk_flags.append(RiskFlag(risk_type="pii_email", severity="medium"))
        if re.search(r"(保证|必赚|100%|稳赚|无风险)", text):
            risk_flags.append(RiskFlag(risk_type="guaranteed_return", severity="high"))

        risk_level = "OK"
        if any(flag.severity == "high" for flag in risk_flags):
            risk_level = "BLOCK"
        elif risk_flags:
            risk_level = "WARN"

        safe_rewrite = ""
        if risk_level == "BLOCK":
            safe_rewrite = await self._get_dynamic_replacement(risk_flags, context)
        elif risk_level == "WARN":
            safe_rewrite = "建议使用合规表达并避免敏感承诺。"

        if risk_level in {"WARN", "BLOCK"}:
            payload = AuditEventPayload(
                event_id=str(uuid.uuid4()),
                session_id=(context or {}).get("session_id") if isinstance(context, dict) else None,
                user_id=(context or {}).get("user_id") if isinstance(context, dict) else None,
                tenant_id=(context or {}).get("tenant_id") if isinstance(context, dict) else None,
                reason="compliance_risk",
                severity="high" if risk_level == "BLOCK" else "medium",
                blocked_content=text if risk_level == "BLOCK" else None,
                risk_score=0.9 if risk_level == "BLOCK" else 0.6,
                details={"stage": stage, "flags": [flag.risk_type for flag in risk_flags]},
            )
            try:
                await bus.publish(EventType.COMPLIANCE_VIOLATION, payload)
            except Exception:
                pass

        return ComplianceResult(risk_level=risk_level, risk_flags=risk_flags, safe_rewrite=safe_rewrite)
