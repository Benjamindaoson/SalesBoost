"""
Golden Dataset 回归测试

确保意图分类、Prompt 等核心逻辑在修改后不退化。
使用 tests/data/golden_dataset.json 中的标注数据。
"""
import json
import pytest
from pathlib import Path

# Golden dataset path
GOLDEN_PATH = Path(__file__).parent.parent / "data" / "golden_dataset.json"


def _load_golden() -> dict:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_intent_regression_keyword_fallback():
    """意图分类回归：使用 keyword 路由（不调用 LLM）"""
    data = _load_golden()
    cases = data.get("intent_regression", [])
    if not cases:
        pytest.skip("golden_dataset.json intent_regression is empty")

    from app.agents.conversation.intent_routing import IntentRouter, UserIntent

    router = IntentRouter()
    intent_map = {
        UserIntent.INFORMATIONAL: "informational",
        UserIntent.SOCIAL: "social",
        UserIntent.OBJECTION: "objection",
        UserIntent.BUYING_SIGNAL: "buying_signal",
        UserIntent.CLARIFICATION: "clarification",
        UserIntent.UNKNOWN: "unknown",
    }

    passed = 0
    for c in cases:
        msg = c.get("message", "")
        expected = c.get("expected_intent", "unknown")
        ctx = {"current_stage": c.get("stage", "discovery")}
        result = router.analyze_intent(msg, ctx)
        got = intent_map.get(result.intent, "unknown")
        if got == expected:
            passed += 1
        else:
            assert got == expected, f"message='{msg}' expected={expected} got={got}"

    assert passed == len(cases), f"Passed {passed}/{len(cases)} intent regression cases"


def test_prompt_hash_regression():
    """Prompt 哈希回归：修改 Prompt 后需更新 golden 或显式接受"""
    data = _load_golden()
    hashes = data.get("prompt_hashes", {})
    if not hashes:
        pytest.skip("golden_dataset.json prompt_hashes not configured")

    from app.core.prompt_registry import get_prompt_hash, load_prompts_from_dir
    from pathlib import Path

    prompts_dir = Path(__file__).parent.parent.parent / "app" / "core" / "prompts"
    load_prompts_from_dir(str(prompts_dir))

    for name, expected_hash in hashes.items():
        if expected_hash is None:
            continue
        current = get_prompt_hash(name)
        assert current == expected_hash, (
            f"Prompt '{name}' hash changed. "
            f"Expected {expected_hash}, got {current}. "
            "Update golden_dataset.json if intentional."
        )
