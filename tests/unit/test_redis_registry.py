import unittest
import time
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.infra.llm.registry import ModelRegistry, ModelMetadata
from app.infra.cache.redis_client import RobustRedisClient
from app.infra.llm.fast_intent import FastIntentClassifier, IntentCategory

class TestPersistentRegistry(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = ModelRegistry()
        # Ensure we start fresh
        self.registry._models = {}
        self.registry._load_defaults()
        
    @patch("app.infra.cache.redis_client.get_redis")
    async def test_redis_fallback_initialization(self, mock_get_redis):
        # Simulate Redis unavailable (returns InMemoryCache)
        from core.redis import InMemoryCache
        mock_get_redis.return_value = InMemoryCache()
        
        # Initialize Registry (triggers redis_client.initialize)
        await self.registry.initialize()
        
        # Verify redis_client is in fallback mode
        from app.infra.cache.redis_client import redis_client
        self.assertFalse(redis_client._is_redis_healthy)
        
    @patch("app.infra.cache.redis_client.get_redis")
    async def test_ewma_update_fallback(self, mock_get_redis):
        # Setup: Redis unavailable
        from core.redis import InMemoryCache
        mock_get_redis.return_value = InMemoryCache()
        await self.registry.initialize()
        
        # Get a model to test
        model = self.registry.list_models()[0]
        initial_score = model.quality_score
        
        # Apply positive feedback (Target=10.0, Alpha=0.05)
        # New Score = Init + 0.05 * (10 - Init)
        # If Init=9.0, New = 9.0 + 0.05 * 1 = 9.05
        await self.registry.update_model_reputation(model.provider, model.model_name, 1.0)
        
        self.assertTrue(model.quality_score > initial_score)
        self.assertAlmostEqual(model.quality_score, initial_score + 0.05 * (10.0 - initial_score), places=4)
        
        # Apply negative feedback (Target=0.0)
        # New = Current + 0.05 * (0 - Current)
        current_score = model.quality_score
        await self.registry.update_model_reputation(model.provider, model.model_name, -1.0)
        
        self.assertTrue(model.quality_score < current_score)
        self.assertEqual(model.negative_feedback_streak, 1)

    @patch("app.infra.cache.redis_client.get_redis")
    async def test_circuit_breaker_logic(self, mock_get_redis):
        # Setup: Redis unavailable
        from core.redis import InMemoryCache
        mock_get_redis.return_value = InMemoryCache()
        await self.registry.initialize()
        
        model = self.registry.list_models()[0]
        model.quality_score = 8.0
        model.negative_feedback_streak = 4
        
        # 5th negative feedback -> Penalty
        await self.registry.update_model_reputation(model.provider, model.model_name, -1.0)
        
        # Should be penalized (halved approx)
        # Expected calculation:
        # Pre-penalty score update: 8.0 + 0.05*(0-8.0) = 8.0 - 0.4 = 7.6
        # Penalty: 7.6 * 0.5 = 3.8
        self.assertAlmostEqual(model.quality_score, 3.8, places=1)
        self.assertEqual(model.negative_feedback_streak, 0) # Reset after penalty

    async def test_fast_intent_stats(self):
        classifier = FastIntentClassifier()
        classifier.classify("Write a poem about AI") # Creative
        classifier.classify("Calculate 2+2") # Logic
        
        stats = classifier.get_stats()
        self.assertEqual(stats[IntentCategory.CREATIVE], 1)
        self.assertEqual(stats[IntentCategory.LOGIC], 1)

    @patch("app.infra.cache.redis_client.get_redis")
    async def test_debounce_buffering(self, mock_get_redis):
        """Test that updates are buffered and flushed"""
        # Setup Redis mock to track calls
        mock_client = AsyncMock()
        # Mock hgetall to return empty dict or valid data to avoid float conversion error
        mock_client.hgetall.return_value = {} 
        mock_get_redis.return_value = mock_client
        
        await self.registry.initialize()
        
        model = self.registry.list_models()[0]
        
        # 1. Add 5 updates (below threshold of 10)
        for _ in range(5):
            await self.registry.update_model_reputation(model.provider, model.model_name, 1.0)
            
        # Should be buffered locally
        key = f"{model.provider}/{model.model_name}"
        self.assertEqual(len(self.registry._feedback_buffer[key]), 5)
        
        # Redis eval should NOT have been called yet (except maybe initialization)
        # Note: initialize calls hgetall, but update uses eval.
        # We need to check eval calls count.
        # Since initialize doesn't use eval, count should be 0.
        self.assertEqual(mock_client.eval.call_count, 0)
        
        # 2. Add 5 more updates (hitting threshold 10)
        for _ in range(5):
            await self.registry.update_model_reputation(model.provider, model.model_name, 1.0)
            
        # Buffer should be cleared (flushed)
        self.assertEqual(len(self.registry._feedback_buffer[key]), 0)
        
        # Wait a bit for async task to run
        await asyncio.sleep(0.1)
        
        # Redis eval SHOULD have been called once with batch
        self.assertEqual(mock_client.eval.call_count, 1)
        
        # Verify args passed to eval (batch string)
        # args: script, numkeys, key, targets_str, alpha, default, time
        call_args = mock_client.eval.call_args
        targets_str = call_args[0][3] # 4th arg
        self.assertIn("10.0,10.0", targets_str)
        self.assertEqual(targets_str.count("10.0"), 10)

if __name__ == "__main__":
    unittest.main()
