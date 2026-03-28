"""Tests for TacticScorer (renamed from PPOPolicy) and TrainablePolicy stub."""
from app.agents.rl.ppo_policy import TacticScorer, TrainablePolicy
import pytest


def test_tactic_scorer_select_action_returns_action_string():
    scorer = TacticScorer()
    result = scorer.select_action({"stage": "discovery", "turn": 1})
    # select_action returns (action_str, value_float)
    action = result[0] if isinstance(result, tuple) else result
    assert isinstance(action, str)
    assert len(action) > 0


def test_tactic_scorer_is_ppo_policy_alias():
    from app.agents.rl.ppo_policy import PPOPolicy
    assert TacticScorer is PPOPolicy


def test_trainable_policy_stub_has_select_action():
    assert hasattr(TrainablePolicy, "select_action")


def test_trainable_policy_stub_has_update():
    assert hasattr(TrainablePolicy, "update")


def test_trainable_policy_select_action_raises():
    policy = TrainablePolicy()
    with pytest.raises(NotImplementedError):
        policy.select_action({})


def test_trainable_policy_update_raises():
    policy = TrainablePolicy()
    with pytest.raises(NotImplementedError):
        policy.update([])
