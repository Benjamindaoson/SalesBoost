"""Quick test to verify FastText is working"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.intent.production_classifier import ProductionIntentClassifier

async def test():
    classifier = ProductionIntentClassifier()

    # Check if model loaded
    if classifier.model:
        print("[OK] FastText model loaded successfully")
    else:
        print("[FAIL] FastText model NOT loaded - using rules fallback")

    # Test classification
    result = await classifier.classify("这个价格太贵了", {})
    print(f"Intent: {result.intent}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Using: {'ML Model' if classifier.model else 'Rules Only'}")

asyncio.run(test())
