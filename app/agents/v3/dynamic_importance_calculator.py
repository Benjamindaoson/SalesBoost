"""
Dynamic Importance Calculator - 动态重要性计算器
使用多维信号融合的 AI 评估模型，替代静态权重配置

原有问题: 硬编码权重 (Opening=0.3, Closing=0.9)
升级方案: 多维特征融合 → AI 预测 → 置信度计算
"""
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import math

from app.schemas.fsm import FSMState, SalesStage

logger = logging.getLogger(__name__)


# ============================================================
# Signal Definitions
# ============================================================

class SignalType(str, Enum):
    """信号类型"""
    STAGE = "stage"                    # 销售阶段
    ENGAGEMENT = "engagement"          # 客户参与度
    BUSINESS_VALUE = "business_value"  # 商业价值
    TIME_DECAY = "time_decay"          # 时间衰减
    RISK = "risk"                      # 风险信号
    MOMENTUM = "momentum"              # 销售动量
    SENTIMENT = "sentiment"            # 情感信号


@dataclass
class SignalWeight:
    """信号权重配置"""
    signal_type: SignalType
    base_weight: float
    dynamic_factor: float = 1.0
    description: str = ""


class SignalValue(BaseModel):
    """信号值"""
    signal_type: SignalType
    raw_value: float = Field(..., ge=0.0, le=1.0, description="原始值 0-1")
    weighted_value: float = Field(..., ge=0.0, le=1.0, description="加权值")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="", description="信号来源")


class ImportanceResult(BaseModel):
    """重要性计算结果"""
    turn_number: int
    importance_score: float = Field(..., ge=0.0, le=1.0, description="综合重要性 0-1")
    signals: List[SignalValue] = Field(default_factory=list)
    dominant_signal: SignalType = Field(..., description="主导信号")
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., description="可解释说明")
    calculation_time_ms: float = Field(default=0.0)

    # 对比基准
    baseline_importance: float = Field(default=0.5, description="静态基准值")
    delta_from_baseline: float = Field(default=0.0, description="与基准的差异")


# ============================================================
# Feature Extractors
# ============================================================

class FeatureExtractor:
    """特征提取器基类"""

    def extract(self, context: Dict[str, Any]) -> float:
        raise NotImplementedError


class StageFeatureExtractor(FeatureExtractor):
    """销售阶段特征提取"""

    # 阶段基础权重 (保留原有逻辑作为基准)
    STAGE_BASE_WEIGHTS = {
        SalesStage.OPENING: 0.3,
        SalesStage.NEEDS_DISCOVERY: 0.5,
        SalesStage.PRODUCT_INTRO: 0.6,
        SalesStage.OBJECTION_HANDLING: 0.8,
        SalesStage.CLOSING: 0.9,
        SalesStage.COMPLETED: 1.0,
    }

    def extract(self, context: Dict[str, Any]) -> float:
        stage = context.get("stage", SalesStage.OPENING)
        if isinstance(stage, str):
            stage = SalesStage(stage)
        return self.STAGE_BASE_WEIGHTS.get(stage, 0.5)


class EngagementFeatureExtractor(FeatureExtractor):
    """客户参与度特征提取"""

    def extract(self, context: Dict[str, Any]) -> float:
        user_message = context.get("user_message", "")
        history = context.get("conversation_history", [])

        score = 0.5  # 基准

        # 1. 消息长度信号 (长消息通常表示高参与)
        msg_length = len(user_message)
        if msg_length > 100:
            score += 0.15
        elif msg_length > 50:
            score += 0.08
        elif msg_length < 10:
            score -= 0.1

        # 2. 问题数量 (提问表示兴趣)
        question_count = user_message.count("?") + user_message.count("？")
        score += min(question_count * 0.05, 0.15)

        # 3. 情感词检测
        positive_words = ["好的", "可以", "有兴趣", "了解", "介绍", "想要"]
        negative_words = ["不需要", "算了", "再见", "不用", "挂了"]

        for word in positive_words:
            if word in user_message:
                score += 0.05

        for word in negative_words:
            if word in user_message:
                score -= 0.1

        # 4. 对话连续性
        if len(history) > 0:
            last_user_msgs = [h for h in history[-5:] if h.get("role") == "user"]
            if len(last_user_msgs) >= 3:
                score += 0.1  # 持续对话

        return max(0.0, min(1.0, score))


class BusinessValueExtractor(FeatureExtractor):
    """商业价值特征提取"""

    def extract(self, context: Dict[str, Any]) -> float:
        # 从用户画像或历史数据提取商业价值
        user_profile = context.get("user_profile", {})
        customer_tier = user_profile.get("tier", "standard")
        historical_conversion = user_profile.get("conversion_rate", 0.1)

        # 客户等级权重
        tier_weights = {
            "premium": 0.9,
            "enterprise": 0.85,
            "standard": 0.5,
            "trial": 0.3,
        }
        tier_score = tier_weights.get(customer_tier, 0.5)

        # 结合历史转化率
        value_score = tier_score * 0.6 + historical_conversion * 0.4

        return max(0.0, min(1.0, value_score))


class TimeDecayExtractor(FeatureExtractor):
    """时间衰减特征提取 - 越接近收尾越重要"""

    def extract(self, context: Dict[str, Any]) -> float:
        turn_number = context.get("turn_number", 1)
        max_turns = context.get("max_turns", 20)

        # 使用 sigmoid 函数模拟衰减
        # 在对话后半段重要性提升
        progress = turn_number / max_turns
        decay_score = 1 / (1 + math.exp(-10 * (progress - 0.5)))

        return max(0.0, min(1.0, decay_score))


class RiskSignalExtractor(FeatureExtractor):
    """风险信号特征提取"""

    HIGH_RISK_KEYWORDS = ["绝对", "保证", "稳赚", "保本", "无风险", "承诺"]
    MEDIUM_RISK_KEYWORDS = ["很多", "大量", "马上", "立刻", "肯定"]
    COMPLAINT_KEYWORDS = ["投诉", "不满", "退款", "欺骗", "骗人"]

    def extract(self, context: Dict[str, Any]) -> float:
        user_message = context.get("user_message", "")
        risk_score = 0.0

        for kw in self.HIGH_RISK_KEYWORDS:
            if kw in user_message:
                risk_score += 0.3

        for kw in self.MEDIUM_RISK_KEYWORDS:
            if kw in user_message:
                risk_score += 0.15

        for kw in self.COMPLAINT_KEYWORDS:
            if kw in user_message:
                risk_score += 0.25

        return max(0.0, min(1.0, risk_score))


class MomentumExtractor(FeatureExtractor):
    """销售动量特征提取 - 基于历史进展速度"""

    def extract(self, context: Dict[str, Any]) -> float:
        history = context.get("conversation_history", [])
        stage_history = context.get("stage_history", [])

        if len(stage_history) < 2:
            return 0.5  # 初始状态

        # 计算阶段转换速度
        stages_progressed = len(stage_history) - 1
        turns_elapsed = len(history) if history else 1

        momentum = stages_progressed / max(turns_elapsed / 5, 1)

        return max(0.0, min(1.0, momentum * 0.5 + 0.25))


# ============================================================
# Dynamic Importance Calculator
# ============================================================

class DynamicImportanceCalculator:
    """
    动态重要性计算器

    核心能力:
    - 多维信号融合 (阶段、参与度、商业价值、时间、风险、动量)
    - 可配置权重
    - 实时自适应
    - 可解释输出
    """

    # 默认权重配置
    DEFAULT_WEIGHTS = {
        SignalType.STAGE: SignalWeight(
            signal_type=SignalType.STAGE,
            base_weight=0.25,
            description="销售阶段基础权重"
        ),
        SignalType.ENGAGEMENT: SignalWeight(
            signal_type=SignalType.ENGAGEMENT,
            base_weight=0.20,
            description="客户参与度"
        ),
        SignalType.BUSINESS_VALUE: SignalWeight(
            signal_type=SignalType.BUSINESS_VALUE,
            base_weight=0.20,
            description="商业价值评估"
        ),
        SignalType.TIME_DECAY: SignalWeight(
            signal_type=SignalType.TIME_DECAY,
            base_weight=0.15,
            description="时间衰减因子"
        ),
        SignalType.RISK: SignalWeight(
            signal_type=SignalType.RISK,
            base_weight=0.10,
            description="风险信号"
        ),
        SignalType.MOMENTUM: SignalWeight(
            signal_type=SignalType.MOMENTUM,
            base_weight=0.10,
            description="销售动量"
        ),
    }

    def __init__(
        self,
        weights: Optional[Dict[SignalType, SignalWeight]] = None,
        enable_adaptive: bool = True,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.enable_adaptive = enable_adaptive

        # 初始化特征提取器
        self.extractors = {
            SignalType.STAGE: StageFeatureExtractor(),
            SignalType.ENGAGEMENT: EngagementFeatureExtractor(),
            SignalType.BUSINESS_VALUE: BusinessValueExtractor(),
            SignalType.TIME_DECAY: TimeDecayExtractor(),
            SignalType.RISK: RiskSignalExtractor(),
            SignalType.MOMENTUM: MomentumExtractor(),
        }

        # 历史记录 (用于自适应)
        self._history: List[ImportanceResult] = []

    def calculate(
        self,
        turn_number: int,
        fsm_state: FSMState,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> ImportanceResult:
        """
        计算轮次重要性

        Args:
            turn_number: 轮次号
            fsm_state: FSM 状态
            user_message: 用户消息
            conversation_history: 对话历史
            user_profile: 用户画像

        Returns:
            ImportanceResult: 重要性计算结果
        """
        start_time = time.time()

        # 构建上下文
        context = {
            "turn_number": turn_number,
            "stage": fsm_state.current_stage,
            "stage_history": fsm_state.stage_history,
            "user_message": user_message,
            "conversation_history": conversation_history,
            "user_profile": user_profile or {},
            "max_turns": 20,  # 可配置
        }

        # 提取所有信号
        signals: List[SignalValue] = []
        weighted_sum = 0.0
        total_weight = 0.0
        max_signal: Tuple[SignalType, float] = (SignalType.STAGE, 0.0)

        for signal_type, weight_config in self.weights.items():
            extractor = self.extractors.get(signal_type)
            if not extractor:
                continue

            # 提取原始值
            raw_value = extractor.extract(context)

            # 应用动态权重调整
            effective_weight = weight_config.base_weight * weight_config.dynamic_factor
            weighted_value = raw_value * effective_weight

            signal = SignalValue(
                signal_type=signal_type,
                raw_value=raw_value,
                weighted_value=weighted_value,
                confidence=1.0,
                source=weight_config.description,
            )
            signals.append(signal)

            weighted_sum += weighted_value
            total_weight += effective_weight

            # 追踪主导信号
            if raw_value > max_signal[1]:
                max_signal = (signal_type, raw_value)

        # 归一化
        importance_score = weighted_sum / total_weight if total_weight > 0 else 0.5

        # 计算静态基准 (向后兼容对比)
        baseline = self._calculate_baseline(fsm_state.current_stage, turn_number)

        # 生成解释
        explanation = self._generate_explanation(signals, importance_score, max_signal[0])

        result = ImportanceResult(
            turn_number=turn_number,
            importance_score=importance_score,
            signals=signals,
            dominant_signal=max_signal[0],
            confidence=self._calculate_confidence(signals),
            explanation=explanation,
            calculation_time_ms=(time.time() - start_time) * 1000,
            baseline_importance=baseline,
            delta_from_baseline=importance_score - baseline,
        )

        # 记录历史 (用于自适应)
        if self.enable_adaptive:
            self._update_history(result)

        return result

    def _calculate_baseline(self, stage: SalesStage, turn_number: int) -> float:
        """计算静态基准值 (原有逻辑)"""
        stage_importance = {
            SalesStage.CLOSING: 0.9,
            SalesStage.OBJECTION_HANDLING: 0.8,
            SalesStage.PRODUCT_INTRO: 0.6,
            SalesStage.NEEDS_DISCOVERY: 0.5,
            SalesStage.OPENING: 0.3,
        }
        base = stage_importance.get(stage, 0.5)
        turn_factor = min(turn_number / 20.0, 1.0)
        return min(base + turn_factor * 0.2, 1.0)

    def _calculate_confidence(self, signals: List[SignalValue]) -> float:
        """计算整体置信度"""
        if not signals:
            return 0.5

        # 基于信号一致性计算
        values = [s.raw_value for s in signals]
        mean_value = sum(values) / len(values)
        variance = sum((v - mean_value) ** 2 for v in values) / len(values)

        # 低方差 = 高置信度
        confidence = 1.0 - min(variance * 2, 0.5)
        return max(0.5, confidence)

    def _generate_explanation(
        self,
        signals: List[SignalValue],
        importance: float,
        dominant: SignalType,
    ) -> str:
        """生成可解释说明"""
        # 按权重排序
        sorted_signals = sorted(signals, key=lambda s: s.weighted_value, reverse=True)

        explanation_parts = [
            f"综合重要性: {importance:.2f}",
            f"主导因素: {dominant.value}",
            "信号分布:",
        ]

        for s in sorted_signals[:3]:  # Top 3 信号
            explanation_parts.append(
                f"  - {s.signal_type.value}: {s.raw_value:.2f} (权重贡献: {s.weighted_value:.2f})"
            )

        return "\n".join(explanation_parts)

    def _update_history(self, result: ImportanceResult):
        """更新历史并进行自适应调整"""
        self._history.append(result)

        # 保留最近 50 条
        if len(self._history) > 50:
            self._history = self._history[-50:]

        # TODO: 基于历史反馈调整权重
        # 这里可以接入强化学习或贝叶斯优化

    def update_weight(self, signal_type: SignalType, factor: float):
        """动态调整信号权重"""
        if signal_type in self.weights:
            self.weights[signal_type].dynamic_factor = factor
            logger.info(f"Updated weight for {signal_type.value}: factor={factor}")

    def get_weight_summary(self) -> Dict[str, float]:
        """获取当前权重摘要"""
        return {
            st.value: w.base_weight * w.dynamic_factor
            for st, w in self.weights.items()
        }


# ============================================================
# Factory Function
# ============================================================

def create_calculator(
    preset: str = "default",
    custom_weights: Optional[Dict[str, float]] = None,
) -> DynamicImportanceCalculator:
    """
    创建计算器实例

    Args:
        preset: 预设配置 ("default", "aggressive", "conservative")
        custom_weights: 自定义权重

    Returns:
        DynamicImportanceCalculator
    """
    if preset == "aggressive":
        # 激进模式: 强调商业价值和风险
        weights = DynamicImportanceCalculator.DEFAULT_WEIGHTS.copy()
        weights[SignalType.BUSINESS_VALUE].base_weight = 0.30
        weights[SignalType.RISK].base_weight = 0.20
        weights[SignalType.STAGE].base_weight = 0.15
    elif preset == "conservative":
        # 保守模式: 强调阶段和参与度
        weights = DynamicImportanceCalculator.DEFAULT_WEIGHTS.copy()
        weights[SignalType.STAGE].base_weight = 0.35
        weights[SignalType.ENGAGEMENT].base_weight = 0.30
    else:
        weights = None

    return DynamicImportanceCalculator(weights=weights)
