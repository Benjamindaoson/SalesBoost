"""Quick suggest service."""
from __future__ import annotations

from typing import List, Optional

from app.agents.roles.compliance_agent import ComplianceAgent
from app.observability.metrics.business_metrics import performance_metrics_collector
from schemas.mvp import IntentLabel, QuickSuggestResponse


class QuickSuggestService:
    def __init__(self) -> None:
        self._compliance = ComplianceAgent()

    async def generate_suggest(
        self,
        session_id: str,
        last_user_msg: str,
        conversation_history=None,
        fsm_state=None,
        optional_context=None,
    ) -> QuickSuggestResponse:
        text = (last_user_msg or "").strip().lower()
        intent = self._classify_intent(text)
        suggested_reply, alt_replies, confidence = self._compose_reply(intent, fsm_state)

        compliance = await self._compliance.check(
            message=suggested_reply,
            stage=(fsm_state or {}).get("current_stage"),
            context=optional_context,
        )
        if compliance.risk_level in {"WARN", "BLOCK"} and compliance.safe_rewrite:
            suggested_reply = compliance.safe_rewrite
            performance_metrics_collector.record_refusal()

        evidence = None
        if optional_context and isinstance(optional_context, dict):
            evidence = optional_context.get("evidence")

        return QuickSuggestResponse(
            intent_label=intent,
            suggested_reply=suggested_reply,
            alt_replies=alt_replies,
            confidence=confidence,
            evidence=evidence,
        )

    def _classify_intent(self, text: str) -> IntentLabel:
        if self._match_any(text, ["退款", "投诉", "违法", "欺诈", "scam", "lawsuit"]):
            return IntentLabel.COMPLIANCE_RISK
        if self._match_any(text, ["多少钱", "价格", "费用", "折扣", "优惠", "benefit", "cost", "price"]):
            return IntentLabel.BENEFIT_QA
        if self._match_any(text, ["太贵", "不需要", "没预算", "考虑", "再说", "objection", "not interested"]):
            return IntentLabel.OBJECTION_HANDLING
        if self._match_any(text, ["可以", "就这样", "下单", "购买", "签约", "closing", "deal"]):
            return IntentLabel.CLOSING_PUSH
        return IntentLabel.OTHER

    def _compose_reply(self, intent: IntentLabel, fsm_state: Optional[dict]) -> tuple[str, List[str], float]:
        stage = (fsm_state or {}).get("current_stage", "training")
        if intent == IntentLabel.BENEFIT_QA:
            return (
                "可以的，我们的核心优势是提升成交率和训练效率。您最关心成本还是效果？",
                [
                    "这款方案重点在提升转化率，您当前最想解决哪一类问题？",
                    "如果预算有限，我们也有分阶段的方案，您更在意哪块价值？",
                ],
                0.72,
            )
        if intent == IntentLabel.OBJECTION_HANDLING:
            return (
                "理解您的顾虑。方便说下主要担心点是价格、时间，还是效果？",
                [
                    "我可以先从最关键的一点开始解释，您更担心哪块？",
                    "我们先对齐目标，再看是否需要继续深入，您看可以吗？",
                ],
                0.68,
            )
        if intent == IntentLabel.CLOSING_PUSH:
            return (
                "好，我们可以先确认目标和时间安排，然后进入下一步流程。",
                [
                    "如果您认可，我们现在就定下试用范围和时间。",
                    "我帮您整理一份确认清单，您看完我们就推进。",
                ],
                0.7,
            )
        if intent == IntentLabel.COMPLIANCE_RISK:
            return (
                "我们需要保持合规表达，我可以改成更稳妥的说法。",
                [
                    "我会用合规的方式说明，确保信息准确。",
                    "我们可以先聚焦事实和可验证的内容。",
                ],
                0.66,
            )
        return (
            f"[{stage}] 明白了。您能再具体说一下最重要的诉求吗？",
            [
                "您最关心的指标是什么？",
                "方便举个例子说明当前的挑战吗？",
            ],
            0.6,
        )

    @staticmethod
    def _match_any(text: str, keywords: List[str]) -> bool:
        return any(key in text for key in keywords)
