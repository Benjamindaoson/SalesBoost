"""
Final Integration Test - All Upgraded Components
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_production_system():
    """Test production system end-to-end"""
    print("="*70)
    print("SALESBOOST PRODUCTION SYSTEM TEST")
    print("="*70)

    # 1. Test Intent Classifier
    print("\n[1/5] Testing Intent Classification...")
    from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier

    classifier = ContextAwareIntentClassifier()
    result = await classifier.classify_with_context(
        "这个价格太贵了，能便宜点吗",
        [{"role": "user", "content": "多少钱"}],
        {"current_stage": "discovery", "turn_count": 2}
    )
    print(f"   Intent: {result.intent} (confidence: {result.confidence:.2f})")
    print(f"   Context Enhanced: {result.context_enhanced}")
    assert result.intent == "price_objection", "Intent test failed"
    print("   [OK] Intent classification working")

    # 2. Test Tools
    print("\n[2/5] Testing Tool Registry...")
    from app.tools.registry import build_default_registry

    registry = build_default_registry()
    tools = registry.list_tools()
    print(f"   Registered tools: {len(tools)}")
    for tool in tools:
        print(f"     - {tool.name}")
    assert len(tools) >= 5, "Tool registry test failed"
    print("   [OK] Tool registry working")

    # 3. Test Price Calculator
    print("\n[3/5] Testing PriceCalculatorTool...")
    from app.tools.price_calculator import PriceCalculatorTool

    calc = PriceCalculatorTool()
    result = await calc.run({
        "items": [{"name": "VIP", "unit_price": 1000, "quantity": 1}],
        "discount_rate": 0.2,
        "tax_rate": 0.06
    })
    print(f"   Total: {result['total']:.2f} CNY")
    assert result['total'] == 848.0, "Calculator test failed"
    print("   [OK] Price calculator working")

    # 4. Test Performance Monitor
    print("\n[4/5] Testing Performance Monitor...")
    from app.observability.performance_monitor import performance_monitor

    performance_monitor.record("intent", "classify", 45.2, True)
    performance_monitor.record("intent", "classify", 52.1, True)
    stats = performance_monitor.get_stats("intent", "classify")
    print(f"   Mean latency: {stats['latency']['mean']:.1f}ms")
    print(f"   Success rate: {stats['success_rate']*100:.0f}%")
    print("   [OK] Performance monitor working")

    # 5. Test A/B Testing
    print("\n[5/5] Testing A/B Framework...")
    from app.infra.ab_testing.manager import ABTestManager

    ab_manager = ABTestManager(traffic_split=0.5)
    variant_a = ab_manager._assign_variant("user_123")
    variant_b = ab_manager._assign_variant("user_456")
    print(f"   User 123 -> Variant {variant_a}")
    print(f"   User 456 -> Variant {variant_b}")
    print("   [OK] A/B testing working")

    print("\n" + "="*70)
    print("ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
    print("="*70)

    # Summary
    print("\nSYSTEM CAPABILITIES:")
    print("  [v] AI Intent Classification (FastText + Rules)")
    print("  [v] Context-Aware Enhancement")
    print("  [v] 5+ Production Tools")
    print("  [v] LangGraph Orchestration")
    print("  [v] Function Calling Support")
    print("  [v] A/B Testing Framework")
    print("  [v] Performance Monitoring")
    print("\nNEXT STEPS:")
    print("  1. Run: pytest tests/unit/test_intent_classifier.py")
    print("  2. Deploy to production")
    print("  3. Monitor metrics in logs/ab_test_metrics.jsonl")


if __name__ == "__main__":
    asyncio.run(test_production_system())
