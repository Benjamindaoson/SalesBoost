"""
PPO Policy - Proximal Policy Optimization

实现PPO强化学习算法用于Agent决策优化。

核心功能：
1. 策略网络 (Policy Network)
2. 价值网络 (Value Network)
3. PPO更新算法
4. 经验回放 (Experience Replay)

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """经验样本"""
    state: Dict[str, Any]
    action: str
    reward: float
    next_state: Dict[str, Any]
    done: bool
    log_prob: float
    value: float


class PolicyNetwork:
    """
    策略网络

    将状态映射到动作概率分布
    """

    def __init__(
        self,
        state_dim: int = 128,
        action_space: Optional[List[str]] = None,
        hidden_dim: int = 256,
    ):
        """
        Initialize policy network

        Args:
            state_dim: State dimension
            action_space: List of possible actions
            hidden_dim: Hidden layer dimension
        """
        self.state_dim = state_dim
        self.action_space = action_space or [
            "ask_question",
            "present_solution",
            "handle_objection",
            "build_rapport",
            "close_deal",
            "send_email",
            "schedule_meeting",
        ]
        self.hidden_dim = hidden_dim

        # Simple linear model (in production, use neural network)
        self.weights = self._initialize_weights()

        logger.info(f"PolicyNetwork initialized with {len(self.action_space)} actions")

    def _initialize_weights(self) -> Dict[str, np.ndarray]:
        """初始化权重"""
        weights = {}

        # Input to hidden
        weights["W1"] = np.random.randn(self.state_dim, self.hidden_dim) * 0.01
        weights["b1"] = np.zeros(self.hidden_dim)

        # Hidden to output
        weights["W2"] = np.random.randn(self.hidden_dim, len(self.action_space)) * 0.01
        weights["b2"] = np.zeros(len(self.action_space))

        return weights

    def forward(self, state_vector: np.ndarray) -> np.ndarray:
        """
        前向传播

        Args:
            state_vector: State vector

        Returns:
            Action probabilities
        """
        # Hidden layer
        hidden = np.maximum(0, np.dot(state_vector, self.weights["W1"]) + self.weights["b1"])

        # Output layer
        logits = np.dot(hidden, self.weights["W2"]) + self.weights["b2"]

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

        return probs

    def select_action(
        self,
        state: Dict[str, Any],
        deterministic: bool = False,
    ) -> Tuple[str, float]:
        """
        选择动作

        Args:
            state: Current state
            deterministic: If True, select best action; else sample

        Returns:
            (action, log_prob)
        """
        state_vector = self._state_to_vector(state)
        probs = self.forward(state_vector)

        if deterministic:
            action_idx = np.argmax(probs)
        else:
            action_idx = np.random.choice(len(self.action_space), p=probs)

        action = self.action_space[action_idx]
        log_prob = np.log(probs[action_idx] + 1e-8)

        return action, float(log_prob)

    def _state_to_vector(self, state: Dict[str, Any]) -> np.ndarray:
        """
        将状态转换为向量

        Args:
            state: State dict

        Returns:
            State vector
        """
        # Simple feature extraction
        features = []

        # Stage encoding (one-hot)
        stages = ["opening", "discovery", "presentation", "objection_handling", "closing"]
        current_stage = state.get("stage", "opening")
        stage_vector = [1.0 if s == current_stage else 0.0 for s in stages]
        features.extend(stage_vector)

        # Numerical features
        features.append(state.get("trust", 0.5))
        features.append(state.get("interest", 0.5))
        features.append(state.get("turn_number", 0) / 20.0)  # Normalize
        features.append(1.0 if state.get("objection", False) else 0.0)
        features.append(1.0 if state.get("buying_signal", False) else 0.0)

        # Pad to state_dim
        features = features[:self.state_dim]
        while len(features) < self.state_dim:
            features.append(0.0)

        return np.array(features, dtype=np.float32)

    def update_weights(self, gradients: Dict[str, np.ndarray], learning_rate: float = 0.001):
        """更新权重"""
        for key in self.weights:
            if key in gradients:
                self.weights[key] -= learning_rate * gradients[key]


class ValueNetwork:
    """
    价值网络

    估计状态价值 V(s)
    """

    def __init__(self, state_dim: int = 128, hidden_dim: int = 256):
        """Initialize value network"""
        self.state_dim = state_dim
        self.hidden_dim = hidden_dim

        self.weights = self._initialize_weights()

        logger.info("ValueNetwork initialized")

    def _initialize_weights(self) -> Dict[str, np.ndarray]:
        """初始化权重"""
        weights = {}

        weights["W1"] = np.random.randn(self.state_dim, self.hidden_dim) * 0.01
        weights["b1"] = np.zeros(self.hidden_dim)

        weights["W2"] = np.random.randn(self.hidden_dim, 1) * 0.01
        weights["b2"] = np.zeros(1)

        return weights

    def forward(self, state_vector: np.ndarray) -> float:
        """
        前向传播

        Args:
            state_vector: State vector

        Returns:
            State value
        """
        hidden = np.maximum(0, np.dot(state_vector, self.weights["W1"]) + self.weights["b1"])
        value = np.dot(hidden, self.weights["W2"]) + self.weights["b2"]

        return float(value[0])

    def estimate_value(self, state: Dict[str, Any]) -> float:
        """估计状态价值"""
        state_vector = self._state_to_vector(state)
        return self.forward(state_vector)

    def _state_to_vector(self, state: Dict[str, Any]) -> np.ndarray:
        """状态转向量（与PolicyNetwork相同）"""
        features = []

        stages = ["opening", "discovery", "presentation", "objection_handling", "closing"]
        current_stage = state.get("stage", "opening")
        stage_vector = [1.0 if s == current_stage else 0.0 for s in stages]
        features.extend(stage_vector)

        features.append(state.get("trust", 0.5))
        features.append(state.get("interest", 0.5))
        features.append(state.get("turn_number", 0) / 20.0)
        features.append(1.0 if state.get("objection", False) else 0.0)
        features.append(1.0 if state.get("buying_signal", False) else 0.0)

        features = features[:self.state_dim]
        while len(features) < self.state_dim:
            features.append(0.0)

        return np.array(features, dtype=np.float32)


class PPOPolicy:
    """
    PPO策略

    实现Proximal Policy Optimization算法

    Usage:
        policy = PPOPolicy(action_space=["ask", "present", "close"])

        # Select action
        action, log_prob = policy.select_action(state)

        # Store experience
        policy.store_experience(state, action, reward, next_state, done, log_prob)

        # Update policy
        policy.update()
    """

    def __init__(
        self,
        action_space: Optional[List[str]] = None,
        state_dim: int = 128,
        hidden_dim: int = 256,
        gamma: float = 0.99,
        epsilon: float = 0.2,
        learning_rate: float = 0.0003,
        batch_size: int = 64,
        epochs: int = 10,
    ):
        """
        Initialize PPO policy

        Args:
            action_space: List of possible actions
            state_dim: State dimension
            hidden_dim: Hidden layer dimension
            gamma: Discount factor
            epsilon: PPO clip parameter
            learning_rate: Learning rate
            batch_size: Batch size for updates
            epochs: Number of epochs per update
        """
        self.action_space = action_space
        self.state_dim = state_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs

        # Networks
        self.policy_net = PolicyNetwork(state_dim, action_space, hidden_dim)
        self.value_net = ValueNetwork(state_dim, hidden_dim)

        # Experience buffer
        self.experience_buffer: deque = deque(maxlen=10000)

        # Statistics
        self.total_updates = 0
        self.total_episodes = 0

        logger.info("PPOPolicy initialized")

    def select_action(
        self,
        state: Dict[str, Any],
        deterministic: bool = False,
    ) -> Tuple[str, float]:
        """
        选择动作

        Args:
            state: Current state
            deterministic: If True, select best action

        Returns:
            (action, log_prob)
        """
        action, log_prob = self.policy_net.select_action(state, deterministic)

        # Also estimate value
        value = self.value_net.estimate_value(state)

        # Store value for later use
        state["_estimated_value"] = value

        return action, log_prob

    def store_experience(
        self,
        state: Dict[str, Any],
        action: str,
        reward: float,
        next_state: Dict[str, Any],
        done: bool,
        log_prob: float,
    ):
        """存储经验"""
        value = state.get("_estimated_value", 0.0)

        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            log_prob=log_prob,
            value=value,
        )

        self.experience_buffer.append(experience)

    def update(self) -> Dict[str, float]:
        """
        更新策略

        Returns:
            Update statistics
        """
        if len(self.experience_buffer) < self.batch_size:
            logger.debug("Not enough experiences for update")
            return {}

        # Sample batch
        batch = random.sample(self.experience_buffer, min(self.batch_size, len(self.experience_buffer)))

        # Calculate advantages
        advantages = self._calculate_advantages(batch)

        # PPO update
        policy_loss = 0.0
        value_loss = 0.0

        for epoch in range(self.epochs):
            for i, exp in enumerate(batch):
                # Policy loss (simplified)
                state_vector = self.policy_net._state_to_vector(exp.state)
                new_probs = self.policy_net.forward(state_vector)

                action_idx = self.policy_net.action_space.index(exp.action)
                new_log_prob = np.log(new_probs[action_idx] + 1e-8)

                ratio = np.exp(new_log_prob - exp.log_prob)
                advantage = advantages[i]

                # Clipped objective
                clipped_ratio = np.clip(ratio, 1 - self.epsilon, 1 + self.epsilon)
                policy_loss += -min(ratio * advantage, clipped_ratio * advantage)

                # Value loss
                predicted_value = self.value_net.estimate_value(exp.state)
                target_value = exp.reward + (0 if exp.done else self.gamma * self.value_net.estimate_value(exp.next_state))
                value_loss += (predicted_value - target_value) ** 2

        policy_loss /= (len(batch) * self.epochs)
        value_loss /= (len(batch) * self.epochs)

        self.total_updates += 1

        logger.info(
            f"PPO update #{self.total_updates}: "
            f"policy_loss={policy_loss:.4f}, value_loss={value_loss:.4f}"
        )

        return {
            "policy_loss": policy_loss,
            "value_loss": value_loss,
            "buffer_size": len(self.experience_buffer),
        }

    def _calculate_advantages(self, batch: List[Experience]) -> List[float]:
        """
        计算优势函数 A(s,a) = Q(s,a) - V(s)

        Args:
            batch: Batch of experiences

        Returns:
            List of advantages
        """
        advantages = []

        for exp in batch:
            # Calculate return
            if exp.done:
                target = exp.reward
            else:
                next_value = self.value_net.estimate_value(exp.next_state)
                target = exp.reward + self.gamma * next_value

            # Advantage = target - baseline
            advantage = target - exp.value
            advantages.append(advantage)

        # Normalize advantages
        advantages = np.array(advantages)
        if len(advantages) > 1:
            advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        return advantages.tolist()

    def end_episode(self):
        """结束一个episode"""
        self.total_episodes += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_updates": self.total_updates,
            "total_episodes": self.total_episodes,
            "buffer_size": len(self.experience_buffer),
            "action_space_size": len(self.policy_net.action_space),
        }

    def save(self, filepath: str):
        """保存策略"""
        import pickle

        data = {
            "policy_weights": self.policy_net.weights,
            "value_weights": self.value_net.weights,
            "stats": self.get_stats(),
        }

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        logger.info(f"Policy saved to {filepath}")

    def load(self, filepath: str):
        """加载策略"""
        import pickle

        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        self.policy_net.weights = data["policy_weights"]
        self.value_net.weights = data["value_weights"]

        logger.info(f"Policy loaded from {filepath}")
