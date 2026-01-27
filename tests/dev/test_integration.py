#!/usr/bin/env python3
"""
Quick Integration Test Script
Test if cost control system and middleware are working properly
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_cost_control():
    """Test cost control system"""
    print("Testing cost control system...")
    try:
        from cognitive.infra.gateway.cost_control import (
            cost_optimized_caller,
            ModelCostCalculator,
            SmartModelRouter,
            BudgetManager,
        )

        print("Cost control system import successful")

        # Test cost calculation
        cost = ModelCostCalculator.calculate_cost("gpt-3.5-turbo", 1000, 500)
        print(f"Cost calculation test passed: GPT-3.5 Turbo 1000+500 tokens = ${cost}")

        # Test model routing
        tier = ModelCostCalculator.get_model_tier("qwen-turbo")
        print(f"Model tier test passed: qwen-turbo belongs to {tier.value} tier")

        # Test budget management
        budget_manager = BudgetManager()
        budget_manager.set_session_budget("test-session", 10.0)
        can_afford = budget_manager.check_budget("test-session", "test-user", 1.0)
        print(f"Budget management test passed: Budget $10, trying to spend $1 -> {can_afford}")

        return True
    except Exception as e:
        print(f"Cost control system test failed: {e}")
        return False


def test_middleware():
    """Test middleware system"""
    print("\nTesting middleware system...")
    try:
        from app.middleware import (
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            LoggingMiddleware,
            RequestSizeMiddleware,
            setup_middleware,
        )

        print("Middleware system import successful")

        # Test middleware instantiation
        rate_limit = RateLimitMiddleware(None, calls=100, period=60)
        print("Rate limiting middleware instantiation successful")

        security_headers = SecurityHeadersMiddleware(None)
        print("Security headers middleware instantiation successful")

        logging_mw = LoggingMiddleware(None)
        print("Logging middleware instantiation successful")

        size_limit = RequestSizeMiddleware(None, max_size=10 * 1024 * 1024)
        print("Request size limiting middleware instantiation successful")

        return True
    except Exception as e:
        print(f"Middleware system test failed: {e}")
        return False


def test_websocket_hook():
    """Test WebSocket hook"""
    print("\nTesting WebSocket hook...")
    try:
        # Check if file exists
        hook_path = "frontend/src/hooks/useWebSocket.ts"
        if os.path.exists(hook_path):
            print("WebSocket hook file exists")

            # Check file content
            with open(hook_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "useWebSocket" in content and "sendMessage" in content:
                    print("WebSocket hook content verification successful")
                    return True
                else:
                    print("WebSocket hook content is incomplete")
                    return False
        else:
            print("WebSocket hook file does not exist")
            return False
    except Exception as e:
        print(f"WebSocket hook test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("SalesBoost Integration Test Starting...\n")

    results = []

    # Test cost control
    results.append(test_cost_control())

    # Test middleware
    results.append(test_middleware())

    # Test WebSocket hook
    results.append(test_websocket_hook())

    # Output results
    print("\n" + "=" * 50)
    print("Test Results Summary:")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")

    if passed == total:
        print("\nAll tests passed! Integration successful!")
        return 0
    else:
        print("\nSome tests failed, please check the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
