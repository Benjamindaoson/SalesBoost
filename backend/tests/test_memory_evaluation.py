from app.evaluation.memory_scenarios import get_memory_scenarios


def test_memory_scenarios_are_defined():
    scenarios = get_memory_scenarios()
    assert len(scenarios) >= 2


def test_memory_scenario_contract():
    for scenario in get_memory_scenarios():
        assert "initial_memory" in scenario
        assert "new_information" in scenario
        assert "expected_update" in scenario
