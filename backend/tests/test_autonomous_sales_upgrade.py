from app.evaluation.golden_sales_cases import get_golden_cases


def test_golden_sales_cases_have_expected_targets():
    cases = get_golden_cases()

    assert len(cases) >= 3

    for case in cases:
        assert case["message"]
        assert case["expected_intent"]
        assert case["expected_stage"]


def test_objection_case_exists():
    cases = get_golden_cases()
    ids = {case["id"] for case in cases}

    assert "objection_price_001" in ids
