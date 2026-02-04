"""
Bandit-Based Tool Selection

Implements contextual multi-armed bandit for intelligent tool routing.
Learns from historical performance to select optimal tools.
"""
import logging
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class BanditArm:
    """Represents a tool (arm) in the bandit"""
    tool_name: str
    pulls: int = 0  # Number of times selected
    total_reward: float = 0.0  # Cumulative reward
    avg_reward: float = 0.0  # Average reward
    last_updated: float = 0.0


class SimpleContextualBandit:
    """
    Simple contextual multi-armed bandit using epsilon-greedy strategy.

    Balances exploration (trying different tools) and exploitation
    (using best-performing tools).
    """

    def __init__(self, epsilon: float = 0.1):
        """
        Initialize bandit.

        Args:
            epsilon: Exploration rate (0-1). Higher = more exploration.
        """
        self.epsilon = epsilon
        self._arms: Dict[str, BanditArm] = {}
        self._decisions: Dict[str, Dict] = {}  # decision_id -> decision info

    def select_arm(
        self,
        available_tools: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Select a tool using epsilon-greedy strategy.

        Args:
            available_tools: List of available tool names
            context: Optional context for contextual selection

        Returns:
            Tuple of (selected_tool, decision_id)
        """
        if not available_tools:
            raise ValueError("No tools available for selection")

        # Initialize arms if needed
        for tool in available_tools:
            if tool not in self._arms:
                self._arms[tool] = BanditArm(tool_name=tool, last_updated=time.time())

        # Epsilon-greedy selection
        if random.random() < self.epsilon:
            # Explore: random selection
            selected_tool = random.choice(available_tools)
            strategy = "explore"
        else:
            # Exploit: select best arm
            available_arms = [self._arms[tool] for tool in available_tools]

            # Handle cold start: if no arm has been pulled, random select
            if all(arm.pulls == 0 for arm in available_arms):
                selected_tool = random.choice(available_tools)
                strategy = "cold_start"
            else:
                # Select arm with highest average reward
                best_arm = max(available_arms, key=lambda a: a.avg_reward if a.pulls > 0 else float('-inf'))
                selected_tool = best_arm.tool_name
                strategy = "exploit"

        # Generate decision ID
        decision_id = f"bandit_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

        # Record decision
        self._decisions[decision_id] = {
            "tool": selected_tool,
            "strategy": strategy,
            "timestamp": time.time(),
            "context": context,
            "available_tools": available_tools
        }

        logger.debug(
            f"Bandit selected {selected_tool} (strategy={strategy}, "
            f"epsilon={self.epsilon}, pulls={self._arms[selected_tool].pulls})"
        )

        return selected_tool, decision_id

    def record_feedback(
        self,
        decision_id: str,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None
    ) -> None:
        """
        Record feedback for a decision.

        Args:
            decision_id: Decision ID from select_arm
            success: Whether execution succeeded
            latency_ms: Execution latency in milliseconds
            error: Optional error message
        """
        if decision_id not in self._decisions:
            logger.warning(f"Unknown decision ID: {decision_id}")
            return

        decision = self._decisions[decision_id]
        tool_name = decision["tool"]

        # Calculate reward
        # Reward = success (1 or 0) - latency_penalty
        # Latency penalty: normalize to 0-1 range (assuming max 5000ms)
        latency_penalty = min(latency_ms / 5000.0, 1.0) * 0.5  # Max 0.5 penalty
        reward = (1.0 if success else 0.0) - latency_penalty

        # Update arm statistics
        arm = self._arms[tool_name]
        arm.pulls += 1
        arm.total_reward += reward
        arm.avg_reward = arm.total_reward / arm.pulls
        arm.last_updated = time.time()

        # Update decision with feedback
        decision["feedback"] = {
            "success": success,
            "latency_ms": latency_ms,
            "reward": reward,
            "error": error,
            "recorded_at": time.time()
        }

        logger.debug(
            f"Recorded feedback for {tool_name}: "
            f"success={success}, latency={latency_ms:.2f}ms, reward={reward:.3f}, "
            f"avg_reward={arm.avg_reward:.3f} (pulls={arm.pulls})"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get bandit statistics.

        Returns:
            Dictionary with statistics for all arms
        """
        arms_stats = {}
        for tool_name, arm in self._arms.items():
            arms_stats[tool_name] = {
                "pulls": arm.pulls,
                "avg_reward": round(arm.avg_reward, 4),
                "total_reward": round(arm.total_reward, 2),
                "last_updated": arm.last_updated
            }

        total_pulls = sum(arm.pulls for arm in self._arms.values())

        return {
            "epsilon": self.epsilon,
            "total_decisions": len(self._decisions),
            "total_pulls": total_pulls,
            "arms": arms_stats
        }

    def get_best_tool(self, available_tools: List[str]) -> Optional[str]:
        """
        Get current best tool (highest avg reward).

        Args:
            available_tools: List of available tools

        Returns:
            Best tool name, or None if no data
        """
        available_arms = [
            self._arms[tool] for tool in available_tools
            if tool in self._arms and self._arms[tool].pulls > 0
        ]

        if not available_arms:
            return None

        best_arm = max(available_arms, key=lambda a: a.avg_reward)
        return best_arm.tool_name

    def reset(self) -> None:
        """Reset all bandit state"""
        self._arms.clear()
        self._decisions.clear()
        logger.info("Bandit state reset")


class ToolSelector:
    """
    Tool selector using bandit algorithm.

    Provides intelligent tool selection based on historical performance.
    """

    def __init__(self, epsilon: Optional[float] = None):
        """
        Initialize tool selector.

        Args:
            epsilon: Exploration rate (default from settings)
        """
        settings = get_settings()
        self.epsilon = epsilon if epsilon is not None else settings.TOOL_BANDIT_EPSILON
        self.bandit = SimpleContextualBandit(epsilon=self.epsilon)
        self.enabled = settings.TOOL_BANDIT_ENABLED

        logger.info(f"ToolSelector initialized (enabled={self.enabled}, epsilon={self.epsilon})")

    def select_tool(
        self,
        tool_group: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Optional[str]]:
        """
        Select best tool from group.

        Args:
            tool_group: List of tool names to choose from
            context: Optional context for selection

        Returns:
            Tuple of (selected_tool, decision_id)
            If bandit disabled, returns (first_tool, None)
        """
        if not self.enabled:
            # Bandit disabled, return first tool
            return tool_group[0] if tool_group else None, None

        return self.bandit.select_arm(tool_group, context)

    def record_feedback(
        self,
        decision_id: str,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Record feedback for a decision"""
        if not self.enabled or not decision_id:
            return

        self.bandit.record_feedback(decision_id, success, latency_ms, error)

    def get_statistics(self) -> Dict[str, Any]:
        """Get selector statistics"""
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            **self.bandit.get_statistics()
        }

    def get_best_tool(self, tool_group: List[str]) -> Optional[str]:
        """Get current best tool from group"""
        if not self.enabled:
            return None

        return self.bandit.get_best_tool(tool_group)


# Global singleton
_tool_selector: Optional[ToolSelector] = None


def get_tool_selector() -> ToolSelector:
    """Get global tool selector instance"""
    global _tool_selector
    if _tool_selector is None:
        _tool_selector = ToolSelector()
    return _tool_selector
