from app.evaluation.golden_sales_benchmark import get_golden_cases


def test_golden_sales_cases_exist():
    cases = get_golden_cases()
    assert len(cases) >= 3
    assert all("expected_intent" in c for c in cases)


def test_cases_have_stage_targets():
    for case in get_golden_sales_cases():
        assert case["expected_stage"]
