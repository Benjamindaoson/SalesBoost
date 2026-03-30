"""
Unit Tests: LiveAssistEngine
============================
Tests the 3-stage AI decision chain:
  - Keyword fallback produces correct structure
  - LLM pipeline degradation: fallback on failure
  - S2 weakness profile loading (mocked Redis)
  - Correct MEDDPICC gap propagation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.live_assist_engine import (
    LiveAssistEngine,
    LiveAssistAnalysis,
    IntentResult,
    StageResult,
    SuggestionResult,
)
from app.services.methodology_engine import MethodologyState, MethodologyFramework


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return LiveAssistEngine()


@pytest.fixture
def methodology_state_with_gaps():
    """MEDDPICC state where economic_buyer and identify_pain are UNKNOWN."""
    state = MethodologyState(framework=MethodologyFramework.MEDDPICC)
    return state  # all dimensions default to UNKNOWN


# ---------------------------------------------------------------------------
# 1. Keyword Fallback Tests (no LLM)
# ---------------------------------------------------------------------------

class TestKeywordFallback:
    def test_objection_message(self, engine, methodology_state_with_gaps):
        analysis = engine._keyword_fallback(
            customer_message="这个价格太贵了，我们预算有限",
            methodology_ctx={},
            weakness_profile={},
        )
        assert analysis.intent.intent_type == "OBJECTION"
        assert analysis.stage.stage == "objection_handling"
        assert len(analysis.suggestions) >= 1
        assert not analysis.personalized

    def test_buying_signal_message(self, engine):
        analysis = engine._keyword_fallback(
            customer_message="好的，我们下一步怎么签合同？",
            methodology_ctx={},
            weakness_profile={},
        )
        assert analysis.intent.intent_type == "BUYING_SIGNAL"
        assert analysis.stage.stage == "closing"

    def test_economic_buyer_gap(self, engine):
        analysis = engine._keyword_fallback(
            customer_message="这件事还没有得到我们老板批准",
            methodology_ctx={},
            weakness_profile={},
        )
        assert analysis.intent.intent_type == "ECONOMIC_BUYER_GAP"
        # MEDDPICC economic_buyer gap should be auto-injected
        assert "economic_buyer" in analysis.stage.methodology_gaps

    def test_unknown_message_gives_listening_suggestion(self, engine):
        analysis = engine._keyword_fallback(
            customer_message="嗯...",
            methodology_ctx={},
            weakness_profile={},
        )
        assert analysis.intent.intent_type == "UNKNOWN"
        assert len(analysis.suggestions) >= 1

    def test_meddpicc_probe_injected_from_context(self, engine):
        ctx = {
            "gaps": [
                {
                    "dimension": "metrics",
                    "label": "Metrics (量化指标)",
                    "probe_questions": ["客户的关键业务指标有哪些？"],
                }
            ]
        }
        analysis = engine._keyword_fallback(
            customer_message="我们现在没什么特别的问题...",
            methodology_ctx=ctx,
            weakness_profile={},
        )
        # Should include a MEDDPICC probe suggestion
        tactics = [s.tactic for s in analysis.suggestions]
        assert any("MEDDPICC" in t for t in tactics)


# ---------------------------------------------------------------------------
# 2. Personalization Tests (S2 weakness profile)
# ---------------------------------------------------------------------------

class TestPersonalization:
    @pytest.mark.asyncio
    async def test_weakness_profile_loaded_from_redis(self, engine):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"top_improvements": ["未能有效挖掘痛点影响"], "recommended_focus": "Implication 问题"}')

        with patch("backend.app.services.live_assist_engine.get_redis", return_value=mock_redis):
            profile = await engine._load_weakness_profile("user_123")

        assert profile["top_improvements"] == ["未能有效挖掘痛点影响"]
        assert profile["recommended_focus"] == "Implication 问题"

    @pytest.mark.asyncio
    async def test_weakness_profile_returns_empty_on_redis_error(self, engine):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection refused"))

        with patch("backend.app.services.live_assist_engine.get_redis", return_value=mock_redis):
            profile = await engine._load_weakness_profile("user_123")

        assert profile == {}


# ---------------------------------------------------------------------------
# 3. LLM Pipeline Degradation Test
# ---------------------------------------------------------------------------

class TestLLMPipelineDegradation:
    @pytest.mark.asyncio
    async def test_falls_back_to_keyword_on_llm_failure(self, engine):
        """If LLM call throws, the engine should NOT raise; it should use keyword fallback."""
        engine.gateway = MagicMock()
        engine.gateway.call = AsyncMock(side_effect=Exception("API key not set"))

        analysis = await engine.analyze(
            customer_message="这个价格太贵了",
            user_id=None,
            enable_llm=True,
        )

        # Should still succeed with keyword fallback
        assert isinstance(analysis, LiveAssistAnalysis)
        assert analysis.intent.intent_type != ""

    @pytest.mark.asyncio
    async def test_disable_llm_flag_skips_llm(self, engine):
        engine.gateway = MagicMock()
        engine.gateway.call = AsyncMock()

        await engine.analyze(
            customer_message="价格太贵了",
            enable_llm=False,
        )
        # LLM should NOT have been called
        engine.gateway.call.assert_not_called()


# ---------------------------------------------------------------------------
# 4. API Response Serialization
# ---------------------------------------------------------------------------

class TestResponseSerialization:
    def test_to_api_response_structure(self):
        analysis = LiveAssistAnalysis(
            intent=IntentResult(intent_type="OBJECTION", confidence=0.85, reasoning="Test"),
            stage=StageResult(stage="objection_handling", confidence=0.78, methodology_gaps=["economic_buyer"]),
            suggestions=[
                SuggestionResult(content="试试TCO法", tactic="总拥有成本法", confidence=0.82, rationale="价格异议场景")
            ],
            personalized=True,
        )
        resp = LiveAssistEngine.to_api_response(analysis)

        assert resp["intent_type"] == "OBJECTION"
        assert resp["intent_confidence"] == 0.85
        assert resp["detected_stage"] == "objection_handling"
        assert resp["stage_confidence"] == 0.78
        assert resp["methodology_gaps"] == ["economic_buyer"]
        assert resp["personalized"] is True
        assert len(resp["suggestions"]) == 1
        assert resp["suggestions"][0]["rationale"] == "价格异议场景"
