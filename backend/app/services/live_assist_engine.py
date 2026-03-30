"""
Live Assist AI Engine
=====================
Implements the 3-stage AI decision chain for real-time sales assistance:

  Customer utterance
      → Stage 1: Intent Recognition   (LLM, structured JSON)
      → Stage 2: Stage Inference      (Hybrid: LLM output + FSM rule check)
      → Stage 3: Strategy Generation  (LLM, context-injected with MEDDPICC gaps + rep weaknesses)

Design principles:
- SINGLE LLM call (all 3 stages in one structured prompt) → < 2s latency
- Graceful fallback to keyword rules if LLM is unavailable
- Personalized coaching via S2 user weakness profile (from Training sessions)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..infra.gateway.model_gateway import ModelGateway
from ..infra.gateway.schemas import ModelCall, RoutingContext
from ..core.redis import get_redis, InMemoryCache
from ..services.methodology_engine import MethodologyEngine, MethodologyState
from ..core.prompt_registry import get_prompt as _get_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------

@dataclass
class IntentResult:
    """Stage 1 output: recognized intent."""
    intent_type: str        # OBJECTION | BUYING_SIGNAL | DISCOVERY | SOCIAL | CLARIFICATION | ECONOMIC_BUYER_GAP | UNKNOWN
    confidence: float       # 0.0 – 1.0
    reasoning: str          # Chain-of-thought rationale (shown in UI)


@dataclass
class StageResult:
    """Stage 2 output: inferred funnel stage."""
    stage: str              # opening | discovery | pitch | objection_handling | closing
    confidence: float       # 0.0 – 1.0
    methodology_gaps: List[str] = field(default_factory=list)  # MEDDPICC dimension keys that are gaps


@dataclass
class SuggestionResult:
    """Stage 3 output: a single suggested response."""
    content: str            # The actual talk-track text
    tactic: str             # e.g. "SPIN-Implication 探询"
    confidence: float       # 0.0 – 1.0
    rationale: str          # Why this tactic was recommended (for UI explainability)


@dataclass
class LiveAssistAnalysis:
    """Full output of the 3-stage pipeline."""
    intent: IntentResult
    stage: StageResult
    suggestions: List[SuggestionResult]
    personalized: bool = False   # True if rep weakness profile was injected


# ---------------------------------------------------------------------------
# Fallback: rule-based keyword detection
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "OBJECTION":           ["贵", "价格", "预算", "太贵", "没钱", "不考虑"],
    "BUYING_SIGNAL":       ["合同", "签约", "什么时候", "开始", "试用", "demo", "下一步"],
    "DISCOVERY":           ["需求", "目前", "现在用", "问题", "困难", "挑战", "帮我"],
    "ECONOMIC_BUYER_GAP":  ["老板", "决策人", "审批", "总裁", "VP", "负责人", "还没批"],
    "CLARIFICATION":       ["什么意思", "不太明白", "能解释", "举个例子", "怎么"],
    "SOCIAL":              ["你好", "初次", "认识", "幸会", "最近"],
}

_STAGE_KEYWORDS: Dict[str, List[str]] = {
    "opening":             ["你好", "初次", "认识", "介绍"],
    "discovery":           ["需求", "目前", "现在用", "问题", "困难", "挑战"],
    "pitch":               ["产品", "方案", "功能", "特点", "优势"],
    "objection_handling":  ["贵", "价格", "预算", "竞品", "担心"],
    "closing":             ["下一步", "合同", "签约", "试用", "demo"],
}


def _keyword_intent(message: str) -> IntentResult:
    msg_lower = message.lower()
    for intent_type, keywords in _INTENT_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return IntentResult(intent_type=intent_type, confidence=0.55, reasoning="Keyword fallback")
    return IntentResult(intent_type="UNKNOWN", confidence=0.30, reasoning="No keyword matched")


def _keyword_stage(message: str) -> str:
    msg_lower = message.lower()
    for stage, keywords in _STAGE_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return stage
    return "discovery"


# ---------------------------------------------------------------------------
# Main Engine
# ---------------------------------------------------------------------------

class LiveAssistEngine:
    """
    3-stage AI decision chain for Live Assist.
    Falls back to keyword rules when LLM is unavailable.
    """

    # Intent types that map directly to MEDDPICC gaps
    _INTENT_TO_MEDDPICC: Dict[str, str] = {
        "ECONOMIC_BUYER_GAP": "economic_buyer",
        "OBJECTION":          "identify_pain",
        "BUYING_SIGNAL":      "decision_process",
    }

    def __init__(self, model_gateway: Optional[ModelGateway] = None):
        self.gateway = model_gateway or ModelGateway()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        customer_message: str,
        user_id: Optional[str] = None,
        methodology_state: Optional[MethodologyState] = None,
        session_id: str = "live",
        enable_llm: bool = True,
    ) -> LiveAssistAnalysis:
        """
        Run the full 3-stage pipeline.
        Falls back to keyword rules if LLM call fails or is disabled.
        """
        weakness_profile = await self._load_weakness_profile(user_id) if user_id else {}
        methodology_coaching_ctx = (
            MethodologyEngine.generate_live_coaching_context(methodology_state)
            if methodology_state else {}
        )

        if enable_llm:
            try:
                return await self._llm_pipeline(
                    customer_message=customer_message,
                    weakness_profile=weakness_profile,
                    methodology_ctx=methodology_coaching_ctx,
                    session_id=session_id,
                )
            except Exception as exc:
                logger.warning("[LiveAssistEngine] LLM pipeline failed, using keyword fallback: %s", exc)

        return self._keyword_fallback(customer_message, methodology_coaching_ctx, weakness_profile)

    # ------------------------------------------------------------------
    # Stage: LLM pipeline (single call, structured JSON output)
    # ------------------------------------------------------------------

    async def _llm_pipeline(
        self,
        customer_message: str,
        weakness_profile: Dict[str, Any],
        methodology_ctx: Dict[str, Any],
        session_id: str,
    ) -> LiveAssistAnalysis:
        """
        Single LLM call that performs Intent Recognition + Stage Inference + Strategy Generation.
        Uses structured JSON output to avoid parsing ambiguity.
        """
        # Build personalization block from S2 weakness profile
        weakness_block = ""
        if weakness_profile and weakness_profile.get("top_improvements"):
            weaknesses = "\n".join(f"  - {w}" for w in weakness_profile["top_improvements"][:3])
            focus = weakness_profile.get("recommended_focus", "")
            weakness_block = f"""
## Rep Weakness Profile (from Training Sessions)
The sales rep has shown these consistent weaknesses in training:
{weaknesses}
Recommended focus area: {focus}
"""

        # Build methodology context block
        methodology_block = ""
        if methodology_ctx.get("gaps"):
            gaps_text = "\n".join(
                f"  - {g['label']}: suggest asking '{g['probe_questions'][0] if g['probe_questions'] else '?'}'"
                for g in methodology_ctx["gaps"][:3]
            )
            score = methodology_ctx.get("score", 0)
            methodology_block = f"""
## MEDDPICC State (from Deal Pipeline)
Current deal score: {score:.0f}/100
Top uncovered gaps (by priority):
{gaps_text}
"""

        # Load system prompt from registry (live_assist_system_prompt.md), fall back to inline
        _tpl = _get_prompt("live_assist_system_prompt")
        if _tpl:
            system_prompt = _tpl.format(
                methodology_block=methodology_block,
                weakness_block=weakness_block,
            )
        else:
            system_prompt = f"""You are a real-time sales copilot AI. A customer just said something during a live sales call.
Your job is to perform a 3-stage analysis and return a single JSON object.

{methodology_block}
{weakness_block}

Analyze the customer utterance and respond with this exact JSON structure:
{{
  "intent": {{
    "intent_type": "<OBJECTION|BUYING_SIGNAL|DISCOVERY|SOCIAL|CLARIFICATION|ECONOMIC_BUYER_GAP|UNKNOWN>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<one sentence explaining the classification>"
  }},
  "stage": {{
    "stage": "<opening|discovery|pitch|objection_handling|closing>",
    "confidence": <0.0 to 1.0>,
    "methodology_gaps": ["<gap_key_1>", "..."]
  }},
  "suggestions": [
    {{
      "content": "<the exact talk-track text in Chinese>",
      "tactic": "<e.g. SPIN-Implication 探询 / 总拥有成本法 / 差异化竞争>",
      "confidence": <0.0 to 1.0>,
      "rationale": "<one sentence: why this tactic fits the situation>"
    }}
  ]
}}

Rules:
- suggestions: provide 2-3 options ordered by confidence (highest first)
- If the rep has weakness profile, the FIRST suggestion should specifically address their weakness
- If MEDDPICC gaps exist, at least one suggestion should contain a probe question for the top gap
- All suggestion content must be in Chinese; tactic names can be bilingual
- Return ONLY the JSON, no markdown fences, no extra text"""

        call = ModelCall(
            prompt=f"Customer said: {customer_message}",
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )
        routing_ctx = RoutingContext(session_id=session_id, agent_type="live_assist")

        raw = await self.gateway.call(call, routing_ctx)
        data = self._parse_llm_json(raw)

        intent = IntentResult(**data["intent"])
        stage = StageResult(**data["stage"])
        suggestions = [SuggestionResult(**s) for s in data.get("suggestions", [])]

        return LiveAssistAnalysis(
            intent=intent,
            stage=stage,
            suggestions=suggestions,
            personalized=bool(weakness_profile),
        )

    def _parse_llm_json(self, raw: str) -> Dict[str, Any]:
        """Robustly parse JSON from LLM output, stripping markdown fences."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        return json.loads(cleaned.strip())

    # ------------------------------------------------------------------
    # Fallback: keyword-based pipeline
    # ------------------------------------------------------------------

    def _keyword_fallback(
        self,
        customer_message: str,
        methodology_ctx: Dict[str, Any],
        weakness_profile: Dict[str, Any],
    ) -> LiveAssistAnalysis:
        intent = _keyword_intent(customer_message)
        stage_str = _keyword_stage(customer_message)
        gaps = [g["dimension"] for g in methodology_ctx.get("gaps", [])[:2]]

        # Map intent to MEDDPICC gap
        meddpicc_dim = self._INTENT_TO_MEDDPICC.get(intent.intent_type)
        if meddpicc_dim and meddpicc_dim not in gaps:
            gaps.insert(0, meddpicc_dim)

        suggestions = self._rule_suggestions(customer_message, stage_str, methodology_ctx)

        return LiveAssistAnalysis(
            intent=intent,
            stage=StageResult(stage=stage_str, confidence=0.55, methodology_gaps=gaps),
            suggestions=suggestions,
            personalized=False,
        )

    def _rule_suggestions(
        self,
        message: str,
        stage: str,
        methodology_ctx: Dict[str, Any],
    ) -> List[SuggestionResult]:
        results: List[SuggestionResult] = []

        if stage == "objection_handling":
            if any(kw in message for kw in ["贵", "价格", "预算"]):
                results.append(SuggestionResult(
                    content="您说得对，单看首年投入确实不低。我们客户平均续约率95%，三年总拥有成本其实更低，我可以给您做一份详细的TCO对比分析。",
                    tactic="总拥有成本法",
                    confidence=0.82,
                    rationale="客户提出价格异议，TCO分析能有效转移焦点至长期价值",
                ))
                results.append(SuggestionResult(
                    content="关于价格，我理解您的顾虑。除了价格，您评估这个项目还有哪些其他的关键考量点？",
                    tactic="SPIN-Implication 探询",
                    confidence=0.75,
                    rationale="通过反问挖掘更多痛点，同时延缓价格谈判",
                ))
            elif any(kw in message for kw in ["竞品", "对比"]):
                results.append(SuggestionResult(
                    content="您在全面评估是非常专业的做法。我们和竞品最大的区别在于实施周期——我们通常6周上线，行业平均3-6个月，这意味着贵司能更快看到回报。",
                    tactic="差异化竞争",
                    confidence=0.78,
                    rationale="竞品对比场景下，用具体量化指标进行差异化定位",
                ))

        if stage == "discovery":
            results.append(SuggestionResult(
                content="能否请您具体描述一下，目前团队在这个环节遇到的最大挑战是什么？这个问题给您的业务带来了哪些具体的影响？",
                tactic="SPIN-Implication 探询",
                confidence=0.70,
                rationale="Discovery阶段核心是挖深痛点，帮客户认识问题的严重性",
            ))

        if stage == "closing":
            results.append(SuggestionResult(
                content="基于我们今天讨论的内容，下一步我建议安排一次详细的方案演示，您看下周三方便吗？",
                tactic="推进成交",
                confidence=0.72,
                rationale="客户显示购买意向，主动推进下一步行动是关键",
            ))

        # Inject MEDDPICC probe question if gaps exist
        if methodology_ctx.get("gaps"):
            top_gap = methodology_ctx["gaps"][0]
            if top_gap.get("probe_questions"):
                results.append(SuggestionResult(
                    content=top_gap["probe_questions"][0],
                    tactic=f"MEDDPICC: 补全 {top_gap.get('label', '')}",
                    confidence=0.65,
                    rationale=f"当前最优先的方法论缺口是「{top_gap.get('label', '')}」，通过探针问题补全",
                ))

        if not results:
            results.append(SuggestionResult(
                content="请您继续说，我非常感兴趣了解更多细节。",
                tactic="积极倾听",
                confidence=0.60,
                rationale="当前意图不明确，积极倾听以获取更多信息",
            ))

        return results[:3]

    # ------------------------------------------------------------------
    # S2: Weakness Profile (from Training Sessions)
    # ------------------------------------------------------------------

    async def _load_weakness_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Load rep's training weakness profile from Redis S2.
        Key: ctx:s2:weakness:{user_id}
        Written by report_generator.py after each Training session.
        """
        key = f"ctx:s2:weakness:{user_id}"
        try:
            client = await get_redis()
            if isinstance(client, InMemoryCache):
                raw = getattr(client, "_store", {}).get(key)
            else:
                raw = await client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.debug("[LiveAssistEngine] Could not load weakness profile for user %s: %s", user_id, exc)
        return {}

    # ------------------------------------------------------------------
    # Response serializer (for API layer)
    # ------------------------------------------------------------------

    @staticmethod
    def to_api_response(analysis: LiveAssistAnalysis) -> Dict[str, Any]:
        """Convert LiveAssistAnalysis to API-safe dict."""
        return {
            "intent_type":      analysis.intent.intent_type,
            "intent_confidence": analysis.intent.confidence,
            "intent_reasoning": analysis.intent.reasoning,
            "detected_stage":   analysis.stage.stage,
            "stage_confidence": analysis.stage.confidence,
            "methodology_gaps": analysis.stage.methodology_gaps,
            "personalized":     analysis.personalized,
            "suggestions": [
                {
                    "content":    s.content,
                    "tactic":     s.tactic,
                    "confidence": s.confidence,
                    "rationale":  s.rationale,
                }
                for s in analysis.suggestions
            ],
        }
