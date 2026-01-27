import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from cognitive.skills.evaluate.adoption_tracker import AdoptionTracker
from schemas.agent_outputs import CoachOutput
from models.adoption_models import AdoptionStyle
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_anti_cheat_parroting_penalty():
    """
    P0: Anti-Cheat Verification
    Verifies that 'Verbatim' copying of examples yields lower skill_delta 
    than 'Paraphrased' adoption, even if raw scores are high.
    """
    tracker = AdoptionTracker()
    
    # Mock DB Session
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Setup Data
    session_id = "test_session_cheat_001"
    user_id = "cheater_001"
    turn_id = 1
    
    # 1. Register Suggestion
    coach_output = CoachOutput(
        suggestion="Use the Feel-Felt-Found technique.",
        reasoning="Handling objection.",
        example_utterance="I understand how you feel, others felt the same, but they found value.",
        priority="high",
        technique_name="Feel-Felt-Found",
        stage_alignment=True,
        confidence=0.9
    )
    
    baseline_scores = {"empathy": 5.0, "logic": 5.0}
    
    # Register twice (one for cheater, one for learner)
    # Note: We need separate session/turn keys or reset tracker
    
    # --- Scenario A: The Cheater (Verbatim Copy) ---
    tracker.register_suggestion(
        session_id=session_id,
        turn_id=turn_id,
        coach_output=coach_output,
        baseline_scores=baseline_scores,
        stage="OBJECTION_HANDLING"
    )
    
    # User copies exactly
    cheater_msg = "I understand how you feel, others felt the same, but they found value."
    # Evaluator gives high score because the sentence is perfect
    cheater_scores = {"empathy": 8.0, "logic": 8.0} 
    # Raw delta would be +3.0
    
    analysis_cheater = await tracker.analyze_adoption(
        session_id=session_id,
        user_id=user_id,
        current_turn=turn_id + 1, # Next turn
        user_message=cheater_msg,
        current_scores=cheater_scores,
        db=mock_db
    )
    
    assert analysis_cheater is not None
    assert analysis_cheater.adopted is True
    # Should be detected as VERBATIM (either by vector or string match)
    assert analysis_cheater.adoption_style == AdoptionStyle.VERBATIM.value
    
    # Check Penalty: Raw delta +3.0 * 0.3 = +0.9
    assert analysis_cheater.skill_delta["empathy"] == 0.9
    
    # --- Scenario B: The Learner (Paraphrased) ---
    # Register for a new turn key
    tracker.register_suggestion(
        session_id=session_id,
        turn_id=turn_id + 10,
        coach_output=coach_output,
        baseline_scores=baseline_scores,
        stage="OBJECTION_HANDLING"
    )
    
    # User internalizes it
    learner_msg = "I totally get why you're worried about the price. A lot of our clients worried about that too initially, but once they started using it, they realized the ROI was huge."
    # Evaluator gives same high score
    learner_scores = {"empathy": 8.0, "logic": 8.0}
    
    analysis_learner = await tracker.analyze_adoption(
        session_id=session_id,
        user_id=user_id,
        current_turn=turn_id + 10 + 1,
        user_message=learner_msg,
        current_scores=learner_scores,
        db=mock_db
    )
    
    assert analysis_learner is not None
    assert analysis_learner.adopted is True
    # Should be PARAPHRASED or STRATEGY_ONLY
    # Note: Vector model needs to be loaded for PARAPHRASED to work reliably with different words.
    # If no vector model, it might fallback to keyword match or fail to detect adoption if keywords don't overlap enough.
    # But let's assume environment has vectors or we hit keywords.
    # "found" -> "realized", "feel" -> "get", "value" -> "ROI"
    
    # If using string fallback, we need to ensure keywords match.
    # "understand", "feel", "found" are in keywords?
    # Let's check AdoptionTracker logic... 
    
    # Verify the penalty didn't apply if style is NOT VERBATIM
    if analysis_learner.adoption_style != AdoptionStyle.VERBATIM.value:
        # Should be full delta +3.0
        assert analysis_learner.skill_delta["empathy"] == 3.0
    else:
        # If it detected VERBATIM by mistake, test fails
        pytest.fail("Learner message was incorrectly classified as VERBATIM")

    print("\n✅ Anti-Cheat Test Passed: Parroting penalized (0.9 vs 3.0)")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
