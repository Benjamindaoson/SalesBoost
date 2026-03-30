"""
Reward Model - 奖励模型

为强化学习提供奖励信号计算。

核心功能：
1. 多维度奖励计算
2. 奖励归一化
3. 奖励塑形 (Reward Shaping)
4. 延迟奖励处理

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class RewardSignalType(str, Enum):
    """奖励信号类型"""
    IMMEDIATE = "immediate"  # 即时奖励
    DELAYED = "delayed"      # 延迟奖励
    SHAPED = "shaped"        # 塑形奖励


@dataclass
class RewardSignal:
    """奖励信号"""
    reward_type: RewardSignalType
    value: float
    components: Dict[str, float]  # 各维度奖励
    metadata: Dict[str, Any]


class RewardModel:
    """
    奖励模型

    计算多维度奖励：
    1. 任务完成奖励 (Task Completion)
    2. 对话质量奖励 (Conversation Quality)
    3. 客户满意度奖励 (Customer Satisfaction)
    4. 效率奖励 (Efficiency)
    5. 合规性奖励 (Compliance)

    Usage:
        reward_model = RewardModel()

        reward = reward_model.calculate_reward(
            customer_response="That sounds interesting!",
            deal_closed=False,
            coach_score=8.5,
            turn_number=5,
            objection_resolved=True
        )
    """

    def __init__(
        self,
        task_weight: float = 0.4,
        quality_weight: float = 0.3,
        satisfaction_weight: float = 0.2,
        efficiency_weight: float = 0.1,
    ):
        """
        Initialize reward model

        Args:
            task_weight: Weight for task completion
            quality_weight: Weight for conversation quality
            satisfaction_weight: Weight for customer satisfaction
            efficiency_weight: Weight for efficiency
        """
        self.task_weight = task_weight
        self.quality_weight = quality_weight
        self.satisfaction_weight = satisfaction_weight
        self.efficiency_weight = efficiency_weight

        # Normalization statistics
        self.reward_history = []
        self.mean_reward = 0.0
        self.std_reward = 1.0

        logger.info("RewardModel initialized")

    def calculate_reward(
        self,
        customer_response: str,
        deal_closed: bool,
        coach_score: Optional[float] = None,
        turn_number: int = 1,
        objection_resolved: bool = False,
        buying_signal: bool = False,
        compliance_violation: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RewardSignal:
        """
        计算综合奖励

        Args:
            customer_response: Customer's response text
            deal_closed: Whether deal was closed
            coach_score: Coach evaluation score (0-10)
            turn_number: Current turn number
            objection_resolved: Whether objection was resolved
            buying_signal: Whether customer showed buying signal
            compliance_violation: Whether there was compliance violation
            metadata: Additional metadata

        Returns:
            Reward signal
        """
        metadata = metadata or {}
        components = {}

        # 1. Task Completion Reward
        task_reward = self._calculate_task_reward(
            deal_closed=deal_closed,
            buying_signal=buying_signal,
            objection_resolved=objection_resolved,
        )
        components["task"] = task_reward

        # 2. Conversation Quality Reward
        quality_reward = self._calculate_quality_reward(
            coach_score=coach_score,
            customer_response=customer_response,
        )
        components["quality"] = quality_reward

        # 3. Customer Satisfaction Reward
        satisfaction_reward = self._calculate_satisfaction_reward(
            customer_response=customer_response,
            buying_signal=buying_signal,
        )
        components["satisfaction"] = satisfaction_reward

        # 4. Efficiency Reward
        efficiency_reward = self._calculate_efficiency_reward(
            turn_number=turn_number,
            deal_closed=deal_closed,
        )
        components["efficiency"] = efficiency_reward

        # 5. Compliance Penalty
        compliance_penalty = -10.0 if compliance_violation else 0.0
        components["compliance"] = compliance_penalty

        # Weighted sum
        total_reward = (
            task_reward * self.task_weight +
            quality_reward * self.quality_weight +
            satisfaction_reward * self.satisfaction_weight +
            efficiency_reward * self.efficiency_weight +
            compliance_penalty
        )

        # Normalize
        normalized_reward = self._normalize_reward(total_reward)

        # Create reward signal
        signal = RewardSignal(
            reward_type=RewardSignalType.IMMEDIATE,
            value=normalized_reward,
            components=components,
            metadata=metadata,
        )

        # Update statistics
        self.reward_history.append(total_reward)
        if len(self.reward_history) > 100:
            self.reward_history.pop(0)
        self._update_normalization_stats()

        logger.debug(
            f"Calculated reward: {normalized_reward:.3f} "
            f"(task={task_reward:.2f}, quality={quality_reward:.2f}, "
            f"satisfaction={satisfaction_reward:.2f}, efficiency={efficiency_reward:.2f})"
        )

        return signal

    def _calculate_task_reward(
        self,
        deal_closed: bool,
        buying_signal: bool,
        objection_resolved: bool,
    ) -> float:
        """计算任务完成奖励"""
        reward = 0.0

        if deal_closed:
            reward += 10.0  # Major reward for closing deal

        if buying_signal:
            reward += 2.0  # Positive signal

        if objection_resolved:
            reward += 1.5  # Successfully handled objection

        return reward

    def _calculate_quality_reward(
        self,
        coach_score: Optional[float],
        customer_response: str,
    ) -> float:
        """计算对话质量奖励"""
        reward = 0.0

        # Use coach score if available
        if coach_score is not None:
            # Normalize coach score (0-10) to reward (-5 to +5)
            reward += (coach_score - 5.0)

        # Analyze customer response sentiment
        sentiment_score = self._analyze_sentiment(customer_response)
        reward += sentiment_score * 2.0

        return reward

    def _calculate_satisfaction_reward(
        self,
        customer_response: str,
        buying_signal: bool,
    ) -> float:
        """计算客户满意度奖励"""
        reward = 0.0

        # Positive keywords
        positive_keywords = [
            "interested", "sounds good", "tell me more", "yes", "sure",
            "感兴趣", "不错", "可以", "好的", "了解"
        ]

        # Negative keywords
        negative_keywords = [
            "not interested", "no thanks", "busy", "not now",
            "不感兴趣", "不需要", "没时间", "不用了"
        ]

        response_lower = customer_response.lower()

        for keyword in positive_keywords:
            if keyword in response_lower:
                reward += 1.0
                break

        for keyword in negative_keywords:
            if keyword in response_lower:
                reward -= 2.0
                break

        if buying_signal:
            reward += 2.0

        return reward

    def _calculate_efficiency_reward(
        self,
        turn_number: int,
        deal_closed: bool,
    ) -> float:
        """计算效率奖励"""
        reward = 0.0

        if deal_closed:
            # Reward faster closing
            if turn_number <= 5:
                reward += 3.0
            elif turn_number <= 10:
                reward += 1.5
            elif turn_number <= 15:
                reward += 0.5
            else:
                reward -= 0.5  # Penalty for taking too long

        # Small penalty for each turn (encourage efficiency)
        reward -= turn_number * 0.1

        return reward

    def _analyze_sentiment(self, text: str) -> float:
        """
        简单情感分析

        Returns:
            Sentiment score (-1.0 to +1.0)
        """
        # Simple keyword-based sentiment
        positive_words = [
            "good", "great", "excellent", "interested", "yes", "sure",
            "好", "不错", "可以", "感兴趣"
        ]
        negative_words = [
            "bad", "no", "not", "never", "don't", "can't",
            "不", "没", "别", "不要"
        ]

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        return (positive_count - negative_count) / total

    def _normalize_reward(self, reward: float) -> float:
        """归一化奖励"""
        if self.std_reward > 0:
            return (reward - self.mean_reward) / (self.std_reward + 1e-8)
        return reward

    def _update_normalization_stats(self):
        """更新归一化统计"""
        if len(self.reward_history) > 10:
            self.mean_reward = np.mean(self.reward_history)
            self.std_reward = np.std(self.reward_history)

    def calculate_shaped_reward(
        self,
        current_state: Dict[str, Any],
        next_state: Dict[str, Any],
        action: str,
    ) -> RewardSignal:
        """
        计算塑形奖励 (Reward Shaping)

        提供中间步骤的奖励引导

        Args:
            current_state: Current state
            next_state: Next state
            action: Action taken

        Returns:
            Shaped reward signal
        """
        components = {}

        # Progress reward
        progress_reward = self._calculate_progress_reward(current_state, next_state)
        components["progress"] = progress_reward

        # Action quality reward
        action_reward = self._calculate_action_reward(action, current_state)
        components["action"] = action_reward

        total_reward = progress_reward + action_reward
        normalized_reward = self._normalize_reward(total_reward)

        return RewardSignal(
            reward_type=RewardSignalType.SHAPED,
            value=normalized_reward,
            components=components,
            metadata={"current_state": current_state, "next_state": next_state},
        )

    def _calculate_progress_reward(
        self,
        current_state: Dict[str, Any],
        next_state: Dict[str, Any],
    ) -> float:
        """计算进度奖励"""
        reward = 0.0

        # State progression
        state_order = ["opening", "discovery", "presentation", "objection_handling", "closing"]

        current_stage = current_state.get("stage", "opening")
        next_stage = next_state.get("stage", "opening")

        if current_stage in state_order and next_stage in state_order:
            current_idx = state_order.index(current_stage)
            next_idx = state_order.index(next_stage)

            if next_idx > current_idx:
                reward += 1.0  # Progressed forward
            elif next_idx < current_idx:
                reward -= 0.5  # Regressed

        # Trust/interest increase
        current_trust = current_state.get("trust", 0.5)
        next_trust = next_state.get("trust", 0.5)
        reward += (next_trust - current_trust) * 2.0

        return reward

    def _calculate_action_reward(self, action: str, state: Dict[str, Any]) -> float:
        """计算动作质量奖励"""
        reward = 0.0

        # Reward appropriate actions for each stage
        stage = state.get("stage", "opening")

        appropriate_actions = {
            "opening": ["greeting", "rapport_building"],
            "discovery": ["ask_question", "listen"],
            "presentation": ["present_solution", "demonstrate_value"],
            "objection_handling": ["acknowledge", "clarify", "resolve"],
            "closing": ["ask_for_commitment", "schedule_meeting"],
        }

        if stage in appropriate_actions:
            if action in appropriate_actions[stage]:
                reward += 0.5

        return reward

    def get_stats(self) -> Dict[str, Any]:
        """获取奖励统计"""
        return {
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "history_length": len(self.reward_history),
            "recent_rewards": self.reward_history[-10:] if self.reward_history else [],
        }
