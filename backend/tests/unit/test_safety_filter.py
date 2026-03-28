"""Tests for SafetyFilter (renamed from ConstitutionalAI) and CritiqueReviseFilter stub."""
import pytest
from app.ai_core.constitutional.constitutional_ai import (
    SafetyFilter,
    CritiqueReviseFilter,
    ConstitutionalAI,
)


def test_safety_filter_is_constitutional_ai_alias():
    assert SafetyFilter is ConstitutionalAI


def test_safety_filter_instantiates():
    sf = SafetyFilter()
    assert sf is not None


def test_safety_filter_has_constitutional_generate():
    assert hasattr(SafetyFilter, "constitutional_generate")


def test_safety_filter_has_get_stats():
    assert hasattr(SafetyFilter, "get_stats")


def test_critique_revise_filter_stub_has_critique_and_revise():
    assert hasattr(CritiqueReviseFilter, "critique_and_revise")


def test_critique_revise_filter_raises():
    crf = CritiqueReviseFilter()
    with pytest.raises(NotImplementedError):
        crf.critique_and_revise()
