"""Unit tests for Intent Classification"""
import pytest
from app.engine.intent.production_classifier import ProductionIntentClassifier
from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier

class TestProductionIntentClassifier:
    @pytest.fixture
    def classifier(self):
        return ProductionIntentClassifier()

    @pytest.mark.asyncio
    async def test_price_objection(self, classifier):
        result = await classifier.classify("这个价格太贵了", {})
        assert result.intent == "price_objection"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_product_inquiry(self, classifier):
        result = await classifier.classify("产品有什么功能", {})
        assert result.intent == "product_inquiry"

class TestContextAwareClassifier:
    @pytest.fixture
    def classifier(self):
        return ContextAwareIntentClassifier()

    @pytest.mark.asyncio
    async def test_repeated_price_pattern(self, classifier):
        history = [
            {"role": "user", "content": "价格多少"},
            {"role": "user", "content": "能便宜点吗"},
        ]
        result = await classifier.classify_with_context(
            "还是太贵",
            history,
            {"current_stage": "discovery", "turn_count": 3}
        )
        assert result.intent == "price_objection"
