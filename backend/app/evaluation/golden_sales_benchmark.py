"""Golden benchmark cases for sales agent regression testing."""

GOLDEN_SALES_CASES = [
    {
        "id": "objection_price_001",
        "category": "objection",
        "input": "这个价格太高了",
        "expected_intent": "OBJECTION",
        "expected_stage": "OBJECTION_HANDLING",
    },
    {
        "id": "discovery_need_001",
        "category": "discovery",
        "input": "我还不知道应该选择哪个方案",
        "expected_intent": "CLARIFICATION",
        "expected_stage": "NEEDS_DISCOVERY",
    },
    {
        "id": "buying_signal_001",
        "category": "buying_signal",
        "input": "什么时候可以安排部署？",
        "expected_intent": "BUYING_SIGNAL",
        "expected_stage": "CLOSING",
    },
]


def get_golden_cases():
    return GOLDEN_SALES_CASES
