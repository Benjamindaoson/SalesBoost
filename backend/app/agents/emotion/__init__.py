"""
Emotion Systems for Agents

提供多维情感模型：
- PAD情感模型 (Pleasure-Arousal-Dominance)
- 情感状态跟踪
- 情感转换规则
"""

from .emotion_model import EmotionModel, EmotionState, EmotionDimension

__all__ = ["EmotionModel", "EmotionState", "EmotionDimension"]
