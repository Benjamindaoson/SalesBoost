"""
LinUCB (Linear Upper Confidence Bound) Contextual Bandit
Advanced bandit algorithm that uses context features to make decisions
"""
import numpy as np
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional
import logging

logger = logging.getLogger(__name__)


class LinUCBBandit:
    """
    LinUCB Contextual Bandit Algorithm

    LinUCB uses linear regression with upper confidence bound to balance
    exploration and exploitation while considering context features.

    Features:
    - Context-aware decision making
    - Confidence-based exploration
    - Online learning from feedback

    Paper: "A Contextual-Bandit Approach to Personalized News Article Recommendation"
    Li et al., 2010

    Usage:
        bandit = LinUCBBandit(
            arms=["npc", "tools", "knowledge"],
            context_dim=10,
            alpha=0.5
        )

        # Make decision
        context = extract_context_features(state)
        decision = bandit.choose(context)

        # Record feedback
        bandit.record_feedback(
            decision_id=decision["decision_id"],
            reward=0.8
        )
    """

    def __init__(
        self,
        arms: List[str],
        context_dim: int = 10,
        alpha: float = 0.5,
        lambda_: float = 1.0
    ):
        """
        Initialize LinUCB bandit

        Args:
            arms: List of arm names (e.g., ["npc", "tools", "knowledge"])
            context_dim: Dimension of context feature vector
            alpha: Exploration parameter (higher = more exploration)
            lambda_: Regularization parameter
        """
        self.arms = arms
        self.context_dim = context_dim
        self.alpha = alpha
        self.lambda_ = lambda_

        # Initialize parameters for each arm
        # A: design matrix (d x d)
        # b: response vector (d x 1)
        self._A = {
            arm: np.identity(context_dim) * lambda_
            for arm in arms
        }
        self._b = {
            arm: np.zeros((context_dim, 1))
            for arm in arms
        }

        # Decision tracking
        self._decisions: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self._arm_pulls = {arm: 0 for arm in arms}
        self._arm_rewards = {arm: 0.0 for arm in arms}

    def choose(
        self,
        context: Dict[str, Any],
        candidates: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        """
        Choose an arm based on context

        Args:
            context: Context dictionary (will be converted to feature vector)
            candidates: Optional subset of arms to consider

        Returns:
            Decision dictionary with chosen arm and metadata
        """
        # Filter candidates
        if candidates:
            valid_arms = [arm for arm in candidates if arm in self.arms]
        else:
            valid_arms = self.arms

        if not valid_arms:
            logger.warning("[LinUCB] No valid arms, defaulting to first arm")
            return {
                "decision_id": uuid.uuid4().hex,
                "chosen": self.arms[0],
                "score": 0.0,
                "ucb": 0.0,
                "exploration": True
            }

        # Convert context to feature vector
        context_vector = self._context_to_features(context)

        # Compute UCB for each arm
        ucb_scores = {}
        theta_estimates = {}

        for arm in valid_arms:
            A_inv = np.linalg.inv(self._A[arm])
            theta = A_inv @ self._b[arm]  # Parameter estimate

            # Expected reward
            expected_reward = (theta.T @ context_vector)[0, 0]

            # Confidence bound
            confidence = self.alpha * np.sqrt(
                (context_vector.T @ A_inv @ context_vector)[0, 0]
            )

            # UCB score
            ucb = expected_reward + confidence

            ucb_scores[arm] = ucb
            theta_estimates[arm] = expected_reward

        # Choose arm with highest UCB
        chosen_arm = max(ucb_scores, key=ucb_scores.get)
        chosen_ucb = ucb_scores[chosen_arm]
        chosen_expected = theta_estimates[chosen_arm]

        # Record decision
        decision_id = uuid.uuid4().hex
        self._decisions[decision_id] = {
            "chosen": chosen_arm,
            "context": context,
            "context_vector": context_vector,
            "timestamp": time.time(),
            "ucb_scores": ucb_scores
        }

        # Update statistics
        self._arm_pulls[chosen_arm] += 1

        return {
            "decision_id": decision_id,
            "chosen": chosen_arm,
            "score": float(chosen_expected),
            "ucb": float(chosen_ucb),
            "exploration": chosen_ucb > chosen_expected + 0.01,  # Exploring if UCB significantly higher
            "all_scores": {arm: float(score) for arm, score in ucb_scores.items()}
        }

    def record_feedback(
        self,
        decision_id: str,
        reward: float,
        signals: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        Record feedback for a decision

        Args:
            decision_id: Decision ID
            reward: Reward value (-1 to 1)
            signals: Additional signals (not used in basic LinUCB)

        Returns:
            True if feedback was recorded
        """
        decision = self._decisions.pop(decision_id, None)
        if not decision:
            logger.warning(f"[LinUCB] Decision {decision_id} not found")
            return False

        chosen_arm = decision["chosen"]
        context_vector = decision["context_vector"]

        # Update parameters
        self._A[chosen_arm] += context_vector @ context_vector.T
        self._b[chosen_arm] += reward * context_vector

        # Update statistics
        self._arm_rewards[chosen_arm] += reward

        logger.debug(
            f"[LinUCB] Feedback recorded: arm={chosen_arm}, "
            f"reward={reward:.3f}, decision_id={decision_id}"
        )

        return True

    def _context_to_features(self, context: Dict[str, Any]) -> np.ndarray:
        """
        Convert context dictionary to feature vector

        Features extracted:
        1. Intent confidence
        2. FSM stage (one-hot encoded)
        3. Need tools (binary)
        4. Risk flags (count)
        5. Recent tool calls (binary)
        6. Turn number (normalized)

        Args:
            context: Context dictionary

        Returns:
            Feature vector (context_dim x 1)
        """
        features = []

        # 1. Intent confidence
        confidence = float(context.get("confidence", 0.5))
        features.append(confidence)

        # 2. FSM stage (one-hot: opening, discovery, demo, negotiation, closing)
        stage = context.get("fsm_stage", "")
        stage_mapping = {
            "opening": [1, 0, 0, 0, 0],
            "discovery": [0, 1, 0, 0, 0],
            "demo": [0, 0, 1, 0, 0],
            "negotiation": [0, 0, 0, 1, 0],
            "closing": [0, 0, 0, 0, 1]
        }
        stage_features = stage_mapping.get(stage, [0, 0, 0, 0, 0])
        features.extend(stage_features)

        # 3. Need tools
        need_tools = 1.0 if context.get("need_tools", False) else 0.0
        features.append(need_tools)

        # 4. Risk flags count (normalized)
        risk_flags = context.get("risk_flags", [])
        risk_count = min(len(risk_flags) / 3.0, 1.0)  # Normalize to [0, 1]
        features.append(risk_count)

        # 5. Recent tool calls
        recent_tools = 1.0 if context.get("recent_tool_calls", False) else 0.0
        features.append(recent_tools)

        # 6. Intent type (one-hot for common intents)
        # This is a simplified version - in production, use proper encoding
        intent = context.get("intent", "")
        # For now, just add a placeholder
        features.append(1.0 if intent else 0.0)

        # Pad or truncate to context_dim
        while len(features) < self.context_dim:
            features.append(0.0)
        features = features[:self.context_dim]

        return np.array(features).reshape(-1, 1)

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for each arm"""
        stats = {}

        for arm in self.arms:
            pulls = self._arm_pulls[arm]
            total_reward = self._arm_rewards[arm]
            avg_reward = total_reward / pulls if pulls > 0 else 0.0

            # Get theta estimate
            A_inv = np.linalg.inv(self._A[arm])
            theta = A_inv @ self._b[arm]

            stats[arm] = {
                "pulls": pulls,
                "total_reward": total_reward,
                "avg_reward": avg_reward,
                "theta_norm": float(np.linalg.norm(theta))
            }

        return stats

    def get_theta(self, arm: str) -> Optional[np.ndarray]:
        """Get parameter estimate for an arm"""
        if arm not in self.arms:
            return None

        A_inv = np.linalg.inv(self._A[arm])
        theta = A_inv @ self._b[arm]
        return theta


class HybridLinUCBBandit(LinUCBBandit):
    """
    Hybrid LinUCB that combines arm-specific and shared features

    This variant learns both:
    - Arm-specific parameters (how each arm responds to context)
    - Shared parameters (general patterns across all arms)

    More powerful but requires more data to converge.
    """

    def __init__(
        self,
        arms: List[str],
        context_dim: int = 10,
        shared_dim: int = 5,
        alpha: float = 0.5,
        lambda_: float = 1.0
    ):
        """
        Initialize Hybrid LinUCB

        Args:
            arms: List of arm names
            context_dim: Dimension of arm-specific context features
            shared_dim: Dimension of shared features
            alpha: Exploration parameter
            lambda_: Regularization parameter
        """
        super().__init__(arms, context_dim, alpha, lambda_)

        self.shared_dim = shared_dim

        # Shared parameters
        self._A0 = np.identity(shared_dim) * lambda_
        self._b0 = np.zeros((shared_dim, 1))

        # Arm-specific parameters for shared features
        self._B = {
            arm: np.zeros((context_dim, shared_dim))
            for arm in arms
        }

    def choose(
        self,
        context: Dict[str, Any],
        candidates: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        """
        Choose arm using hybrid features

        This is a simplified implementation - full Hybrid LinUCB is more complex
        """
        # For now, fall back to standard LinUCB
        # Full implementation would combine arm-specific and shared features
        return super().choose(context, candidates)
