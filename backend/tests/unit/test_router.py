import pytest
from app.infra.gateway.schemas import RoutingContext, AgentType, LatencyMode
from app.infra.llm.router import router
from app.infra.llm.registry import model_registry

@pytest.fixture
def base_context():
    return RoutingContext(
        agent_type=AgentType.COACH,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=10.0,
        latency_mode=LatencyMode.SLOW,
        retrieval_confidence=0.9,
        turn_number=1,
        session_id="test_session",
        budget_authorized=True
    )

def test_router_high_risk(base_context):
    base_context.risk_level = "high"
    config = router.select_model(base_context)
    # High risk requires Quality > 9.0
    # Expected: gpt-4o or claude-3-5-sonnet
    meta = model_registry.get_model(config.provider, config.model_name)
    assert meta.quality_score >= 9.0

def test_router_low_budget(base_context):
    base_context.budget_remaining = 0.005 # < 0.01
    config = router.select_model(base_context)
    # Should pick cheap model
    meta = model_registry.get_model(config.provider, config.model_name)
    assert meta.input_cost_per_1k <= 0.001

def test_router_fast_mode(base_context):
    base_context.latency_mode = LatencyMode.FAST
    base_context.agent_type = AgentType.INTENT_GATE
    config = router.select_model(base_context)
    # Should favor low latency
    meta = model_registry.get_model(config.provider, config.model_name)
    # We weighted latency heavily for INTENT_GATE
    # Check if it picked a fast model (e.g. Gemini Flash or GPT-3.5)
    assert meta.avg_latency_ms <= 500

def test_router_fallback(base_context):
    # Force a scenario where no model works?
    # Hard to force with current logic unless we mock registry.
    # But if we set constraints impossible?
    # e.g. High Risk + Low Budget might filter all out.
    base_context.risk_level = "high" # Needs > 9.0 (Expensive)
    base_context.budget_remaining = 0.001 # Needs < 0.001 (Cheap)
    
    # GPT-4o is expensive (filtered by budget)
    # DeepSeek is cheap (filtered by risk < 9.0, it is 8.5)
    # Gemini Flash is cheap (filtered by risk < 9.0, it is 8.8)
    
    # Result: Fallback to Gemini Flash (hardcoded in router)
    config = router.select_model(base_context)
    assert config.model_name == "gemini-2.0-flash"

def test_router_intent_logic(base_context):
    # Context: INTENT_GATE usually prefers Fast models (Latency > Quality)
    base_context.agent_type = AgentType.INTENT_GATE
    base_context.latency_mode = LatencyMode.FAST
    
    # Prompt: Heavy Logic
    prompt = "Please calculate the compound interest for a $1M investment over 20 years at 5% rate, and write a python script for it."
    
    # Logic intent should boost Quality weight (4.0) and lower Latency weight (0.5)
    # So it should pick a High Quality model (GPT-4o/Claude) despite being INTENT_GATE
    
    config = router.select_model(base_context, prompt=prompt)
    meta = model_registry.get_model(config.provider, config.model_name)
    
    # Quality should be high
    assert meta.quality_score >= 9.0
    # And it likely picked a slower model
    assert meta.avg_latency_ms > 500
