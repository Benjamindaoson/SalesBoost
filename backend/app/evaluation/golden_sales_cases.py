"""Golden scenarios for autonomous sales agent regression testing."""

GOLDEN_SALES_CASES = [
    {
        "id": "objection_price_001",
        "category": "objection",
        "message": "这个价格太高了，有没有优惠？",
        "expected_intent": "OBJECTION",
        "expected_stage": "OBJECTION_HANDLING",
    },
    {
        "id": "discovery_need_001",
        "category": "discovery",
        "message": "我还不知道应该选择哪个方案",
        "expected_intent": "CLARIFICATION",
        "expected_stage": "NEEDS_DISCOVERY",
    },
    {
        "id": "buying_signal_001",
        "category": "buying_signal",
        "message": "什么时候可以安排部署？",
        "expected_intent": "BUYING_SIGNAL",
        "expected_stage": "CLOSING",
    },
]


def get_golden_cases():
    return list(GOLDEN_SALES_CASES)
