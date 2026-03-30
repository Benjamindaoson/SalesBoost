"""
LLM-based Intent Classifier for Sales Conversations

方案 A: 用 LLM 替代 keyword 意图分类，提升准确率至 ~90%。
当 ENABLE_LLM_INTENT=true 时启用，否则回退到 keyword 路由。
Prompt 由 prompt_registry 统一管理，支持版本与回归测试。
"""
import json
import logging
from typing import Any, Dict, Optional

from ..agents.conversation.intent_routing import IntentAnalysis, IntentRouter, UserIntent
from ..infra.gateway.model_gateway import ModelGateway
from ..infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode

logger = logging.getLogger(__name__)


def _get_intent_prompt(message: str, stage: str) -> str:
    """从 prompt_registry 获取意图分类 Prompt"""
    try:
        from ..core.prompt_registry import get_prompt
        tpl = get_prompt("intent_classifier_prompt", version=None)
        if tpl:
            return tpl.format(message=message[:500], stage=stage)
    except Exception as e:
        logger.debug("Prompt registry not available for intent: %s", e)
    return f'用户消息："{message[:500]}"\n当前销售阶段：{stage}\n仅返回 JSON: {{"intent": "...", "confidence": 0.0-1.0, "reasoning": "...", "requires_rag": true/false, "suggested_action": "..."}}'


class LLMIntentClassifier:
    """LLM 驱动的销售意图分类器"""

    def __init__(self, gateway: Optional[ModelGateway] = None):
        self.gateway = gateway or ModelGateway()
        self.keyword_fallback = IntentRouter()

    async def classify(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentAnalysis:
        """分类用户意图，LLM 失败时回退到 keyword"""
        context = context or {}
        stage = context.get("current_stage", "discovery")

        try:
            prompt = _get_intent_prompt(message, stage)
            call = ModelCall(prompt=prompt, system_prompt="你只输出 JSON，不要其他内容。")
            ctx = RoutingContext(
                session_id=context.get("session_id", "intent"),
                agent_type=AgentType.COACH,
                turn_importance=0.3,
                risk_level="low",
                budget_remaining=10.0,
                latency_mode=LatencyMode.FAST,
                retrieval_confidence=1.0,
                turn_number=0,
                budget_authorized=True,
            )
            raw = await self.gateway.call(call, ctx)
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
            data = json.loads(raw)

            intent_map = {
                "informational": UserIntent.INFORMATIONAL,
                "social": UserIntent.SOCIAL,
                "objection": UserIntent.OBJECTION,
                "buying_signal": UserIntent.BUYING_SIGNAL,
                "clarification": UserIntent.CLARIFICATION,
                "unknown": UserIntent.UNKNOWN,
            }
            intent = intent_map.get(
                (data.get("intent") or "unknown").lower(),
                UserIntent.UNKNOWN,
            )
            return IntentAnalysis(
                intent=intent,
                confidence=float(data.get("confidence", 0.8)),
                keywords=[],
                reasoning=str(data.get("reasoning", "")),
                requires_rag=bool(data.get("requires_rag", intent == UserIntent.INFORMATIONAL)),
                suggested_action=str(data.get("suggested_action", "")),
            )
        except Exception as e:
            logger.warning("LLM intent classification failed, fallback to keyword: %s", e)
            return self.keyword_fallback.analyze_intent(message, context)


llm_intent_classifier = LLMIntentClassifier()
