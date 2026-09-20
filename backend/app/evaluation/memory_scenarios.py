"""Memory evaluation scenarios for autonomous sales agent."""


MEMORY_SCENARIOS = [
    {
        "id": "budget_update_001",
        "initial_memory": {
            "budget": "500k",
            "priority": "throughput"
        },
        "new_information": {
            "budget": "300k"
        },
        "expected_update": "latest_budget_should_override_stale_budget",
    },
    {
        "id": "requirement_refinement_001",
        "initial_memory": {
            "need": "basic_solution"
        },
        "new_information": {
            "need": "enterprise_solution"
        },
        "expected_update": "customer_requirement_should_be_updated",
    },
]


def get_memory_scenarios():
    return MEMORY_SCENARIOS
