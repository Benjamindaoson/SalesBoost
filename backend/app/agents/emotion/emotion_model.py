"""
Emotion Model - 多维情感模型

基于PAD (Pleasure-Arousal-Dominance) 模型实现情感计算。

PAD模型三个维度：
1. Pleasure (愉悦度): 正面/负面情绪 (-1.0 to +1.0)
2. Arousal (激活度): 平静/兴奋程度 (0.0 to 1.0)
3. Dominance (支配度): 控制感/被控制感 (-1.0 to +1.0)

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EmotionDimension(str, Enum):
    """情感维度"""
    PLEASURE = "pleasure"      # 愉悦度
    AROUSAL = "arousal"        # 激活度
    DOMINANCE = "dominance"    # 支配度


@dataclass
class EmotionState:
    """情感状态"""
    pleasure: float  # -1.0 to +1.0
    arousal: float   # 0.0 to 1.0
    dominance: float  # -1.0 to +1.0

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "pleasure": self.pleasure,
            "arousal": self.arousal,
            "dominance": self.dominance,
        }

    def get_emotion_label(self) -> str:
        """
        获取情感标签

        基于PAD值映射到具体情感
        """
        p, a, d = self.pleasure, self.arousal, self.dominance

        # High pleasure
        if p > 0.3:
            if a > 0.6:
                return "excited" if d > 0 else "delighted"
            else:
                return "content" if d > 0 else "relaxed"

        # Low pleasure
        elif p < -0.3:
            if a > 0.6:
                return "angry" if d > 0 else "anxious"
            else:
                return "bored" if d > 0 else "sad"

        # Neutral pleasure
        else:
            if a > 0.6:
                return "alert" if d > 0 else "surprised"
            else:
                return "calm" if d > 0 else "neutral"

    def get_mood_score(self) -> float:
        """
        获取综合情绪分数 (0.0 to 1.0)

        用于向后兼容单一mood值
        """
        # Weighted combination
        score = (
            self.pleasure * 0.6 +  # Pleasure is most important
            (self.arousal - 0.5) * 0.2 +  # Moderate arousal is good
            self.dominance * 0.2
        )

        # Normalize to 0-1
        return (score + 1.0) / 2.0


class EmotionModel:
    """
    多维情感模型

    核心功能：
    1. PAD三维情感表示
    2. 情感动态更新
    3. 情感衰减
    4. 情感一致性维护
    5. 人格特质影响

    Usage:
        emotion = EmotionModel(personality="skeptical")

        # Update from message
        emotion.update_from_message(
            message="That sounds interesting!",
            sales_technique="SPIN"
        )

        # Get current state
        state = emotion.get_state()
        print(f"Emotion: {state.get_emotion_label()}")
        print(f"Mood: {state.get_mood_score():.2f}")
    """

    def __init__(
        self,
        personality: str = "neutral",
        initial_pleasure: float = 0.0,
        initial_arousal: float = 0.5,
        initial_dominance: float = 0.0,
        decay_rate: float = 0.1,
    ):
        """
        Initialize emotion model

        Args:
            personality: Personality type (affects emotion dynamics)
            initial_pleasure: Initial pleasure value
            initial_arousal: Initial arousal value
            initial_dominance: Initial dominance value
            decay_rate: Emotion decay rate (0.0 to 1.0)
        """
        self.personality = personality
        self.decay_rate = decay_rate

        # Current emotion state
        self.pleasure = initial_pleasure
        self.arousal = initial_arousal
        self.dominance = initial_dominance

        # Personality baseline (emotions tend to return to this)
        self.baseline = self._get_personality_baseline(personality)

        # Emotion history
        self.history: List[EmotionState] = []

        # Statistics
        self.total_updates = 0

        logger.info(f"EmotionModel initialized with personality: {personality}")

    def _get_personality_baseline(self, personality: str) -> EmotionState:
        """
        获取人格基线情感

        不同人格有不同的情感基线
        """
        baselines = {
            "enthusiastic": EmotionState(pleasure=0.5, arousal=0.7, dominance=0.3),
            "skeptical": EmotionState(pleasure=-0.2, arousal=0.4, dominance=0.2),
            "analytical": EmotionState(pleasure=0.0, arousal=0.3, dominance=0.4),
            "friendly": EmotionState(pleasure=0.3, arousal=0.5, dominance=0.0),
            "busy": EmotionState(pleasure=-0.1, arousal=0.8, dominance=0.3),
            "cautious": EmotionState(pleasure=0.0, arousal=0.6, dominance=-0.2),
            "neutral": EmotionState(pleasure=0.0, arousal=0.5, dominance=0.0),
        }

        return baselines.get(personality, baselines["neutral"])

    def update_from_message(
        self,
        message: str,
        sales_technique: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        根据消息更新情感

        Args:
            message: Message text
            sales_technique: Sales technique used (e.g., "SPIN", "FAB")
            metadata: Additional metadata
        """
        metadata = metadata or {}

        # Analyze message sentiment
        sentiment = self._analyze_sentiment(message)

        # Calculate emotion changes
        delta_pleasure = 0.0
        delta_arousal = 0.0
        delta_dominance = 0.0

        # 1. Sentiment impact
        delta_pleasure += sentiment * 0.3

        # 2. Sales technique impact
        if sales_technique:
            technique_impact = self._get_technique_impact(sales_technique)
            delta_pleasure += technique_impact["pleasure"]
            delta_arousal += technique_impact["arousal"]
            delta_dominance += technique_impact["dominance"]

        # 3. Content analysis
        content_impact = self._analyze_content(message)
        delta_pleasure += content_impact["pleasure"]
        delta_arousal += content_impact["arousal"]
        delta_dominance += content_impact["dominance"]

        # 4. Personality modulation
        delta_pleasure *= self._get_personality_modifier("pleasure")
        delta_arousal *= self._get_personality_modifier("arousal")
        delta_dominance *= self._get_personality_modifier("dominance")

        # Apply changes
        self.pleasure = np.clip(self.pleasure + delta_pleasure, -1.0, 1.0)
        self.arousal = np.clip(self.arousal + delta_arousal, 0.0, 1.0)
        self.dominance = np.clip(self.dominance + delta_dominance, -1.0, 1.0)

        # Apply decay towards baseline
        self._apply_decay()

        # Record history
        self.history.append(self.get_state())
        if len(self.history) > 100:
            self.history.pop(0)

        self.total_updates += 1

        logger.debug(
            f"Emotion updated: {self.get_state().get_emotion_label()} "
            f"(P={self.pleasure:.2f}, A={self.arousal:.2f}, D={self.dominance:.2f})"
        )

    def _analyze_sentiment(self, text: str) -> float:
        """
        分析文本情感

        Returns:
            Sentiment score (-1.0 to +1.0)
        """
        positive_words = [
            "good", "great", "excellent", "wonderful", "amazing", "love", "like",
            "interested", "yes", "sure", "definitely", "absolutely",
            "好", "不错", "很好", "棒", "喜欢", "感兴趣", "可以", "当然"
        ]

        negative_words = [
            "bad", "terrible", "awful", "hate", "dislike", "no", "not", "never",
            "don't", "can't", "won't", "refuse", "reject",
            "不好", "糟糕", "讨厌", "不", "没", "别", "不要", "拒绝"
        ]

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        return (positive_count - negative_count) / total

    def _get_technique_impact(self, technique: str) -> Dict[str, float]:
        """
        获取销售技巧对情感的影响

        Args:
            technique: Sales technique

        Returns:
            Impact on each dimension
        """
        impacts = {
            "SPIN": {
                "pleasure": 0.1,  # Thoughtful questions are pleasant
                "arousal": 0.05,  # Slightly engaging
                "dominance": -0.05,  # Customer feels in control
            },
            "FAB": {
                "pleasure": 0.15,  # Features/benefits are appealing
                "arousal": 0.1,  # Exciting
                "dominance": 0.0,
            },
            "hard_sell": {
                "pleasure": -0.2,  # Pushy is unpleasant
                "arousal": 0.15,  # Creates tension
                "dominance": -0.15,  # Customer feels pressured
            },
            "rapport_building": {
                "pleasure": 0.2,  # Friendly connection
                "arousal": -0.05,  # Calming
                "dominance": 0.05,  # Feels respected
            },
            "objection_handling": {
                "pleasure": 0.05,  # Concerns addressed
                "arousal": -0.1,  # Reduces anxiety
                "dominance": 0.1,  # Feels heard
            },
        }

        return impacts.get(technique, {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.0})

    def _analyze_content(self, message: str) -> Dict[str, float]:
        """分析消息内容对情感的影响"""
        impact = {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.0}

        message_lower = message.lower()

        # Questions increase arousal
        if "?" in message:
            impact["arousal"] += 0.05

        # Exclamation increases arousal
        if "!" in message:
            impact["arousal"] += 0.1

        # Pricing/cost mentions
        if any(word in message_lower for word in ["price", "cost", "expensive", "价格", "费用", "贵"]):
            impact["pleasure"] -= 0.1
            impact["arousal"] += 0.05

        # Benefits/value mentions
        if any(word in message_lower for word in ["benefit", "value", "save", "gain", "权益", "价值", "节省"]):
            impact["pleasure"] += 0.1

        # Pressure words
        if any(word in message_lower for word in ["now", "today", "limited", "hurry", "现在", "今天", "限时"]):
            impact["arousal"] += 0.15
            impact["dominance"] -= 0.1

        return impact

    def _get_personality_modifier(self, dimension: str) -> float:
        """
        获取人格对情感变化的调节系数

        不同人格对情感刺激的敏感度不同
        """
        modifiers = {
            "enthusiastic": {"pleasure": 1.5, "arousal": 1.3, "dominance": 1.0},
            "skeptical": {"pleasure": 0.7, "arousal": 0.8, "dominance": 1.2},
            "analytical": {"pleasure": 0.8, "arousal": 0.6, "dominance": 1.1},
            "friendly": {"pleasure": 1.3, "arousal": 1.0, "dominance": 0.9},
            "busy": {"pleasure": 0.9, "arousal": 1.4, "dominance": 1.1},
            "cautious": {"pleasure": 0.8, "arousal": 1.2, "dominance": 0.8},
            "neutral": {"pleasure": 1.0, "arousal": 1.0, "dominance": 1.0},
        }

        personality_mods = modifiers.get(self.personality, modifiers["neutral"])
        return personality_mods.get(dimension, 1.0)

    def _apply_decay(self):
        """应用情感衰减，向基线回归"""
        self.pleasure += (self.baseline.pleasure - self.pleasure) * self.decay_rate
        self.arousal += (self.baseline.arousal - self.arousal) * self.decay_rate
        self.dominance += (self.baseline.dominance - self.dominance) * self.decay_rate

    def get_state(self) -> EmotionState:
        """获取当前情感状态"""
        return EmotionState(
            pleasure=self.pleasure,
            arousal=self.arousal,
            dominance=self.dominance,
        )

    def get_mood_score(self) -> float:
        """获取综合情绪分数 (0.0 to 1.0)"""
        return self.get_state().get_mood_score()

    def get_emotion_label(self) -> str:
        """获取情感标签"""
        return self.get_state().get_emotion_label()

    def is_positive(self) -> bool:
        """是否处于正面情绪"""
        return self.pleasure > 0.2

    def is_engaged(self) -> bool:
        """是否处于参与状态（高激活度）"""
        return self.arousal > 0.6

    def is_receptive(self) -> bool:
        """是否处于接受状态（正面+适度激活+适度支配）"""
        return (
            self.pleasure > 0.1 and
            0.3 < self.arousal < 0.8 and
            self.dominance > -0.3
        )

    def get_response_tendency(self) -> str:
        """
        获取响应倾向

        基于当前情感状态预测客户可能的响应类型
        """
        state = self.get_state()

        if state.pleasure > 0.3 and state.arousal > 0.5:
            return "enthusiastic"  # 热情响应

        elif state.pleasure > 0.1 and state.arousal < 0.5:
            return "agreeable"  # 同意但平静

        elif state.pleasure < -0.3:
            if state.arousal > 0.6:
                return "resistant"  # 抗拒
            else:
                return "disinterested"  # 不感兴趣

        elif abs(state.pleasure) < 0.2 and state.arousal > 0.6:
            return "curious"  # 好奇

        else:
            return "neutral"  # 中性

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "personality": self.personality,
            "current_state": self.get_state().to_dict(),
            "emotion_label": self.get_emotion_label(),
            "mood_score": self.get_mood_score(),
            "response_tendency": self.get_response_tendency(),
            "total_updates": self.total_updates,
            "history_length": len(self.history),
        }

    def reset(self):
        """重置到基线状态"""
        self.pleasure = self.baseline.pleasure
        self.arousal = self.baseline.arousal
        self.dominance = self.baseline.dominance
        self.history.clear()
        self.total_updates = 0

        logger.info("Emotion model reset to baseline")
