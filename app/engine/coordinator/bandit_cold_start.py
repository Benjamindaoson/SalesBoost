"""
Bandit Cold Start Strategy Implementation
==========================================

Implements warm-up period and default arm weights to handle the cold start problem
for LinUCB bandit algorithm.
"""

import logging
import random
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BanditColdStartManager:
    """
    Manages the cold start phase for bandit algorithms.

    During cold start:
    1. Forces exploration to gather initial data
    2. Uses default arm weights based on domain knowledge
    3. Gradually transitions to learned policy
    """

    def __init__(
        self,
        warmup_pulls: int = 1000,
        default_rewards: Optional[Dict[str, float]] = None
    ):
        """
        Initialize cold start manager.

        Args:
            warmup_pulls: Number of pulls before transitioning to learned policy
            default_rewards: Initial reward estimates for each arm
        """
        self.warmup_pulls = warmup_pulls
        self.total_pulls = 0

        # Default arm weights based on domain knowledge
        self.default_rewards = default_rewards or {
            "npc": 0.7,       # NPC responses generally effective
            "tools": 0.6,     # Tools useful but may be slower
            "knowledge": 0.5  # Knowledge base hit-or-miss
        }

        logger.info(
            f"Cold start manager initialized: warmup_pulls={warmup_pulls}, "
            f"default_rewards={self.default_rewards}"
        )

    def is_warmup_phase(self) -> bool:
        """Check if still in warmup phase."""
        return self.total_pulls < self.warmup_pulls

    def get_warmup_progress(self) -> float:
        """Get warmup progress as percentage (0.0 to 1.0)."""
        return min(1.0, self.total_pulls / self.warmup_pulls)

    def should_force_exploration(self) -> bool:
        """
        Decide if should force exploration.

        During early warmup (first 30%), always explore.
        During mid warmup (30-70%), explore with decreasing probability.
        During late warmup (70-100%), use learned policy with high exploration.
        """
        if not self.is_warmup_phase():
            return False

        progress = self.get_warmup_progress()

        if progress < 0.3:
            # Early phase: always explore
            return True
        elif progress < 0.7:
            # Mid phase: explore with decreasing probability
            explore_prob = 1.0 - (progress - 0.3) / 0.4  # 1.0 → 0.6
            return random.random() < explore_prob
        else:
            # Late phase: mostly use learned policy
            return random.random() < 0.3

    def select_exploration_arm(self, arms: list) -> str:
        """
        Select arm during forced exploration.

        Uses weighted random selection based on default rewards.
        """
        # Calculate selection weights
        weights = [self.default_rewards.get(arm, 0.5) for arm in arms]
        total_weight = sum(weights)

        if total_weight == 0:
            # Fallback to uniform random
            return random.choice(arms)

        # Weighted random selection
        r = random.random() * total_weight
        cumulative = 0
        for arm, weight in zip(arms, weights):
            cumulative += weight
            if r <= cumulative:
                return arm

        return arms[-1]  # Fallback

    def record_pull(self):
        """Record that a pull was made."""
        self.total_pulls += 1

        # Log phase transitions
        if self.total_pulls == int(self.warmup_pulls * 0.3):
            logger.info("Cold start: Entering mid-warmup phase (30%)")
        elif self.total_pulls == int(self.warmup_pulls * 0.7):
            logger.info("Cold start: Entering late-warmup phase (70%)")
        elif self.total_pulls == self.warmup_pulls:
            logger.info("Cold start: Warmup complete! Transitioning to learned policy")

    def get_phase_name(self) -> str:
        """Get current phase name for monitoring."""
        if not self.is_warmup_phase():
            return "learned"

        progress = self.get_warmup_progress()
        if progress < 0.3:
            return "warmup_early"
        elif progress < 0.7:
            return "warmup_mid"
        else:
            return "warmup_late"

    def initialize_bandit_with_priors(self, bandit):
        """
        Initialize bandit with prior knowledge.

        Simulates successful pulls for each arm based on default rewards.
        """
        logger.info("Initializing bandit with prior knowledge...")

        for arm, reward in self.default_rewards.items():
            # Simulate 10 pulls with the default reward
            for _ in range(10):
                # Create dummy context (will be ignored for initialization)
                dummy_context = {
                    "intent": "initialization",
                    "confidence": 1.0,
                    "fsm_stage": "init",
                    "need_tools": False,
                    "risk_flags": [],
                    "recent_tool_calls": False
                }

                # Make decision (will select this arm due to initialization)
                decision = bandit.choose(dummy_context, force_arm=arm)

                # Record the default reward
                bandit.record_feedback(
                    decision_id=decision["decision_id"],
                    reward=reward
                )

        logger.info(
            f"Bandit initialized with {len(self.default_rewards)} arms, "
            f"10 pulls each"
        )


# Integration with LinUCB Bandit
def integrate_cold_start_with_bandit():
    """
    Example integration with LinUCBBandit.

    Add this to app/engine/coordinator/bandit_linucb.py:
    """
    example_code = '''
    from app.engine.coordinator.bandit_cold_start import BanditColdStartManager

    class LinUCBBandit:
        def __init__(self, arms, context_dim, alpha=0.5):
            # ... existing initialization ...

            # Add cold start manager
            self.cold_start = BanditColdStartManager(
                warmup_pulls=1000,
                default_rewards={
                    "npc": 0.7,
                    "tools": 0.6,
                    "knowledge": 0.5
                }
            )

            # Initialize with priors
            self.cold_start.initialize_bandit_with_priors(self)

        def choose(self, context):
            # Check if should force exploration
            if self.cold_start.should_force_exploration():
                arm = self.cold_start.select_exploration_arm(self.arms)
                self.cold_start.record_pull()

                # Record metric
                from app.observability import coordinator_metrics
                coordinator_metrics.record_bandit_phase(
                    phase=self.cold_start.get_phase_name()
                )

                return {
                    "chosen": arm,
                    "ucb": 0.0,
                    "exploration": True,
                    "cold_start": True,
                    "decision_id": self._generate_decision_id()
                }

            # Normal LinUCB selection
            self.cold_start.record_pull()
            return self._linucb_select(context)
    '''

    return example_code


if __name__ == "__main__":
    # Demo
    manager = BanditColdStartManager(warmup_pulls=100)

    print("Cold Start Demo")
    print("=" * 60)

    arms = ["npc", "tools", "knowledge"]

    for i in range(120):
        if manager.is_warmup_phase():
            if manager.should_force_exploration():
                arm = manager.select_exploration_arm(arms)
                print(f"Pull {i+1}: EXPLORE → {arm} (phase: {manager.get_phase_name()})")
            else:
                print(f"Pull {i+1}: EXPLOIT (phase: {manager.get_phase_name()})")
        else:
            print(f"Pull {i+1}: LEARNED POLICY")

        manager.record_pull()

        # Show progress at milestones
        if i + 1 in [30, 70, 100]:
            print(f"  → Progress: {manager.get_warmup_progress()*100:.0f}%")
            print()
