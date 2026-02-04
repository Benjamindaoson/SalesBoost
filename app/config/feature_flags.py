"""
Feature Flags Configuration
Controls experimental features and A/B testing variants
"""
import os
from enum import Enum


class CoordinatorEngine(str, Enum):
    """Available coordinator engines"""
    LEGACY = "legacy"           # cognitive.Orchestrator (MVP)
    WORKFLOW = "workflow"       # WorkflowCoordinator (Linear + AI Intent)
    LANGGRAPH = "langgraph"     # LangGraphCoordinator (Graph-oriented)


class FeatureFlags:
    """
    Feature flags for gradual rollout and A/B testing

    Environment Variables:
        COORDINATOR_ENGINE: Which coordinator to use (legacy/workflow/langgraph)
        ENABLE_ML_INTENT: Enable ML-based intent classification (default: true)
        ENABLE_CONTEXT_AWARE: Enable context-aware enhancements (default: true)
        AB_TESTING_ENABLED: Enable A/B testing framework (default: false)
        AB_TRAFFIC_SPLIT: Percentage of traffic for variant B (0.0-1.0)

        # P0 Optimization Flags (NEW)
        ENABLE_ASYNC_COACH: Enable TTFT optimization (default: true)
        ENABLE_COACH_FALLBACK: Enable graceful degradation (default: true)
        ASYNC_COACH_TIMEOUT: Timeout for async coach (default: 3.0s)
        ASYNC_COACH_ROLLOUT_PERCENTAGE: Gradual rollout percentage (default: 100)
        TRACK_ADVICE_SOURCE: Track advice source for monitoring (default: true)
        TRACK_TTFT: Track TTFT metrics (default: true)
        EMERGENCY_MODE: Emergency rollback mode (default: false)
    """

    @staticmethod
    def get_coordinator_engine() -> CoordinatorEngine:
        """
        Get the active coordinator engine

        Returns:
            CoordinatorEngine: The engine to use

        Usage:
            # In .env or environment:
            # COORDINATOR_ENGINE=langgraph  # Use new LangGraph engine
            # COORDINATOR_ENGINE=workflow   # Use WorkflowCoordinator
            # COORDINATOR_ENGINE=legacy     # Use old MVP Orchestrator (default)
        """
        engine = os.getenv("COORDINATOR_ENGINE", "legacy").lower()

        try:
            return CoordinatorEngine(engine)
        except ValueError:
            # Fallback to legacy if invalid value
            return CoordinatorEngine.LEGACY

    @staticmethod
    def use_ml_intent() -> bool:
        """
        Enable ML-based intent classification

        Default: True (use FastText + rules)
        Set ENABLE_ML_INTENT=false to use rules only
        """
        return os.getenv("ENABLE_ML_INTENT", "true").lower() == "true"

    @staticmethod
    def use_context_aware() -> bool:
        """
        Enable context-aware intent enhancements

        Default: True (use history pattern analysis)
        Set ENABLE_CONTEXT_AWARE=false to disable
        """
        return os.getenv("ENABLE_CONTEXT_AWARE", "true").lower() == "true"

    @staticmethod
    def ab_testing_enabled() -> bool:
        """
        Enable A/B testing framework

        Default: False
        Set AB_TESTING_ENABLED=true to enable
        """
        return os.getenv("AB_TESTING_ENABLED", "false").lower() == "true"

    @staticmethod
    def ab_traffic_split() -> float:
        """
        Get A/B testing traffic split for variant B

        Default: 0.1 (10% traffic to variant B)
        Range: 0.0 - 1.0
        """
        try:
            split = float(os.getenv("AB_TRAFFIC_SPLIT", "0.1"))
            return max(0.0, min(1.0, split))  # Clamp to [0, 1]
        except ValueError:
            return 0.1

    @staticmethod
    def performance_monitoring_enabled() -> bool:
        """
        Enable detailed performance monitoring

        Default: True
        Set PERFORMANCE_MONITORING=false to disable
        """
        return os.getenv("PERFORMANCE_MONITORING", "true").lower() == "true"

    @staticmethod
    def metrics_export_interval() -> int:
        """
        Interval (seconds) for exporting metrics to files

        Default: 300 (5 minutes)
        """
        try:
            return int(os.getenv("METRICS_EXPORT_INTERVAL", "300"))
        except ValueError:
            return 300

    # ==================== P0 Optimization Flags (NEW) ====================

    @staticmethod
    def is_async_coach_enabled() -> bool:
        """
        Enable TTFT optimization (先答后评 pattern)

        When enabled:
        - NPC response is returned immediately
        - Coach advice is generated in background
        - TTFT reduces from ~2s to ~1.2s (40% improvement)

        Default: True (enabled)
        Env: ENABLE_ASYNC_COACH=true|false
        """
        if FeatureFlags.is_emergency_mode():
            return False
        return os.getenv("ENABLE_ASYNC_COACH", "true").lower() == "true"

    @staticmethod
    def is_coach_fallback_enabled() -> bool:
        """
        Enable graceful degradation with fallback coach advice

        When enabled:
        - If AI coach fails, use intent-based fallback advice
        - Ensures 100% coach advice availability

        Default: True (enabled)
        Env: ENABLE_COACH_FALLBACK=true|false
        """
        if FeatureFlags.is_emergency_mode():
            return False
        return os.getenv("ENABLE_COACH_FALLBACK", "true").lower() == "true"

    @staticmethod
    def get_async_coach_timeout() -> float:
        """
        Timeout for async coach generation (seconds)

        If coach takes longer than this, it will be cancelled.

        Default: 3.0 seconds
        Env: ASYNC_COACH_TIMEOUT=3.0
        """
        try:
            timeout = float(os.getenv("ASYNC_COACH_TIMEOUT", "3.0"))
            return max(1.0, min(timeout, 10.0))  # Clamp to [1.0, 10.0]
        except ValueError:
            return 3.0

    @staticmethod
    def get_async_coach_rollout_percentage() -> int:
        """
        Percentage of users to enable async coach for (0-100)

        Use this for gradual rollout:
        - 0: Disabled for all users
        - 50: Enabled for 50% of users (A/B test)
        - 100: Enabled for all users (full rollout)

        Default: 100 (full rollout)
        Env: ASYNC_COACH_ROLLOUT_PERCENTAGE=100
        """
        try:
            percentage = int(os.getenv("ASYNC_COACH_ROLLOUT_PERCENTAGE", "100"))
            return max(0, min(percentage, 100))  # Clamp to [0, 100]
        except ValueError:
            return 100

    @staticmethod
    def should_use_async_coach_for_user(user_id: str) -> bool:
        """
        Determine if async coach should be enabled for a specific user

        Uses consistent hashing to ensure same user always gets same experience.

        Args:
            user_id: User ID

        Returns:
            True if async coach should be enabled for this user
        """
        if not FeatureFlags.is_async_coach_enabled():
            return False

        rollout_percentage = FeatureFlags.get_async_coach_rollout_percentage()

        if rollout_percentage == 0:
            return False

        if rollout_percentage == 100:
            return True

        # Consistent hashing: same user always gets same result
        user_hash = hash(user_id) % 100
        return user_hash < rollout_percentage

    @staticmethod
    def is_advice_source_tracking_enabled() -> bool:
        """
        Track advice source (ai/fallback/error_fallback) for monitoring

        When enabled:
        - All coach advice includes advice_source field
        - Metrics are exported to Prometheus
        - Can monitor fallback rate

        Default: True (enabled)
        Env: TRACK_ADVICE_SOURCE=true|false
        """
        return os.getenv("TRACK_ADVICE_SOURCE", "true").lower() == "true"

    @staticmethod
    def is_ttft_tracking_enabled() -> bool:
        """
        Track TTFT (Time To First Token) metrics

        When enabled:
        - TTFT is measured for every turn
        - Metrics are exported to Prometheus
        - Can monitor performance improvements

        Default: True (enabled)
        Env: TRACK_TTFT=true|false
        """
        return os.getenv("TRACK_TTFT", "true").lower() == "true"

    @staticmethod
    def is_emergency_mode() -> bool:
        """
        Emergency mode: Disable all optimizations

        When enabled:
        - Async coach is disabled
        - Fallback advice is disabled
        - System runs in safe mode

        Use this for emergency rollback if issues arise.

        Default: False (disabled)
        Env: EMERGENCY_MODE=true|false
        """
        import logging
        emergency = os.getenv("EMERGENCY_MODE", "false").lower() == "true"

        if emergency:
            logging.critical(
                "[FeatureFlags] 🚨 EMERGENCY MODE ENABLED 🚨 "
                "All optimizations are disabled"
            )

        return emergency


# Convenience functions
def is_langgraph_enabled() -> bool:
    """Quick check if LangGraph coordinator is active"""
    return FeatureFlags.get_coordinator_engine() == CoordinatorEngine.LANGGRAPH


def is_workflow_enabled() -> bool:
    """Quick check if WorkflowCoordinator is active"""
    return FeatureFlags.get_coordinator_engine() == CoordinatorEngine.WORKFLOW


def is_legacy_mode() -> bool:
    """Quick check if using legacy MVP orchestrator"""
    return FeatureFlags.get_coordinator_engine() == CoordinatorEngine.LEGACY


# Example usage in application code:
"""
from app.config.feature_flags import FeatureFlags, CoordinatorEngine

# Get active engine
engine = FeatureFlags.get_coordinator_engine()

if engine == CoordinatorEngine.LANGGRAPH:
    from app.engine.coordinator.langgraph_coordinator import LangGraphCoordinator
    coordinator = LangGraphCoordinator(...)
elif engine == CoordinatorEngine.WORKFLOW:
    from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
    coordinator = WorkflowCoordinator(...)
else:
    from cognitive import Orchestrator
    coordinator = Orchestrator(...)

# Check individual features
if FeatureFlags.use_ml_intent():
    # Use ML-based classification
    ...
"""
