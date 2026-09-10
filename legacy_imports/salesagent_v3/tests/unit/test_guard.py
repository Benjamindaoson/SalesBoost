"""Unit tests for Guard rules and rewriting."""
from __future__ import annotations

import pytest

from salesagent.core.constants import GuardRiskType
from salesagent.guard.rules import check_sentence, get_risk_severity


def test_guard_false_promise_detection():
    """Test detection of false promises."""
    sentence = "我们保证100%成功，绝对没问题！"
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.FALSE_PROMISE


def test_guard_price_leak_detection():
    """Test detection of price leaks."""
    sentence = "我们的成本只有100元，内部价格是200元。"
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.PRICE_LEAK


def test_guard_competitor_defamation_detection():
    """Test detection of competitor defamation."""
    sentence = "竞品根本不行，他们的产品很垃圾。"
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.COMPETITOR_DEFAMATION


def test_guard_sensitive_info_detection():
    """Test detection of sensitive information."""
    sentence = "我们的真实毛利率是50%，这个客户叫张三。"
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.SENSITIVE_INFO


def test_guard_unauthorized_commitment_detection():
    """Test detection of unauthorized commitments."""
    # Test sentence with clear unauthorized commitment pattern
    sentence = "我帮你申请特批折扣，终身免费维护。"
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.UNAUTHORIZED_COMMITMENT


def test_guard_clean_sentence():
    """Test that clean sentences pass through."""
    sentence = "我们的产品在行业内有着优秀的口碑，欢迎了解。"
    risk_type = check_sentence(sentence)
    assert risk_type is None


def test_guard_risk_severity_low():
    """Test low severity risk detection."""
    sentence = "我们会努力确保成功。"
    risk_type, severity = get_risk_severity(sentence)
    assert risk_type is None or severity <= 0.3


def test_guard_risk_severity_high():
    """Test high severity risk detection."""
    sentence = "我保证100%成功，绝对没问题，一定能做到！"
    risk_type, severity = get_risk_severity(sentence)
    assert risk_type == GuardRiskType.FALSE_PROMISE
    assert severity >= 0.3


def test_guard_risk_severity_critical():
    """Test critical risk types get boosted severity."""
    sentence = "这个客户叫张三，我们的真实毛利是50%。"
    risk_type, severity = get_risk_severity(sentence)
    assert risk_type == GuardRiskType.SENSITIVE_INFO
    assert severity >= 0.5  # Boosted for critical type


def test_guard_english_patterns():
    """Test English pattern detection."""
    sentence = "We guarantee 100% success with our product."
    risk_type = check_sentence(sentence)
    assert risk_type == GuardRiskType.FALSE_PROMISE

    sentence2 = "Their product is terrible and much worse than ours."
    risk_type2 = check_sentence(sentence2)
    assert risk_type2 == GuardRiskType.COMPETITOR_DEFAMATION
