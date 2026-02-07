from app.infra.llm.fast_intent import fast_intent_classifier, IntentCategory


def test_fast_intent_logic_zh():
    r = fast_intent_classifier.classify("请帮我修复这个报错，并给出代码实现。")
    assert r.category == IntentCategory.LOGIC
    assert r.latency_ms >= 0.0


def test_fast_intent_extraction_zh():
    r = fast_intent_classifier.classify("请把下面内容总结成要点列表，并输出 JSON 格式。")
    assert r.category == IntentCategory.EXTRACTION


def test_fast_intent_creative_zh():
    r = fast_intent_classifier.classify("帮我写一篇产品宣传文案，要求有标题和卖点。")
    assert r.category == IntentCategory.CREATIVE


def test_fast_intent_chat_zh():
    r = fast_intent_classifier.classify("你好，今天天气怎么样？")
    assert r.category == IntentCategory.SIMPLE_CHAT

