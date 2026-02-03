"""
Context-Aware Intent Classifier

Enhances intent classification by considering conversation history and FSM state.
"""
import logging
from typing import List, Dict, Any
from collections import Counter

from app.engine.intent.production_classifier import ProductionIntentClassifier
from app.engine.intent.schemas import IntentResult
from app.observability.prometheus_exporter import monitor_intent_classification

logger = logging.getLogger(__name__)


class ContextAwareIntentClassifier:
    """
    Context-aware intent classifier

    Analyzes conversation history and user patterns to improve classification accuracy.
    """

    def __init__(self, base_classifier: ProductionIntentClassifier = None):
        """
        Initialize context-aware classifier

        Args:
            base_classifier: Base classifier to use (defaults to ProductionIntentClassifier)
        """
        self.base_classifier = base_classifier or ProductionIntentClassifier()
        self.context_window_size = 5  # Consider last 5 turns

    @monitor_intent_classification
    async def classify_with_context(
        self,
        message: str,
        history: List[Dict[str, str]],
        fsm_state: Dict[str, Any]
    ) -> IntentResult:
        """
        Classify intent with full conversation context

        Args:
            message: Current user message
            history: Conversation history [{"role": "user|assistant", "content": "..."}]
            fsm_state: FSM state dict with current_stage, turn_count, etc.

        Returns:
            Enhanced IntentResult
        """
        # 1. Base classification
        context = {
            "current_stage": fsm_state.get("current_stage"),
            "turn_count": fsm_state.get("turn_count", 0)
        }

        base_result = await self.base_classifier.classify(message, context)

        # 2. Analyze conversation history patterns
        pattern_analysis = self._analyze_history_patterns(history)

        # 3. Apply pattern-based adjustments
        enhanced_result = self._apply_pattern_adjustments(
            base_result,
            pattern_analysis,
            fsm_state
        )

        # 4. FSM stage calibration
        enhanced_result = self._calibrate_with_fsm_state(
            enhanced_result,
            fsm_state
        )

        # 5. Turn count adjustments
        enhanced_result = self._adjust_for_turn_count(
            enhanced_result,
            fsm_state.get("turn_count", 0)
        )

        return enhanced_result

    def _analyze_history_patterns(
        self,
        history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in conversation history

        Returns:
            Dictionary with pattern analysis results
        """
        recent_history = history[-self.context_window_size:]
        user_messages = [
            msg["content"]
            for msg in recent_history
            if msg.get("role") == "user"
        ]

        analysis = {
            "price_mention_count": 0,
            "product_question_count": 0,
            "positive_signals": 0,
            "hesitation_signals": 0,
            "has_repeated_pattern": False
        }

        # Count patterns in user messages
        for msg in user_messages:
            msg_lower = msg.lower()

            # Price mentions
            if any(word in msg_lower for word in ["price", "价格", "多少钱", "费用", "cost"]):
                analysis["price_mention_count"] += 1

            # Product questions
            if any(word in msg_lower for word in ["功能", "feature", "怎么", "how", "what"]):
                analysis["product_question_count"] += 1

            # Positive signals
            if any(word in msg_lower for word in ["好", "不错", "可以", "good", "great", "interested"]):
                analysis["positive_signals"] += 1

            # Hesitation signals
            if any(word in msg_lower for word in ["考虑", "想想", "think", "maybe", "not sure"]):
                analysis["hesitation_signals"] += 1

        # Check for repeated patterns
        if analysis["price_mention_count"] >= 2:
            analysis["has_repeated_pattern"] = True

        return analysis

    def _apply_pattern_adjustments(
        self,
        result: IntentResult,
        patterns: Dict[str, Any],
        fsm_state: Dict[str, Any]
    ) -> IntentResult:
        """Apply adjustments based on detected patterns"""

        # Repeated price mentions → Strong price objection
        if patterns["price_mention_count"] >= 2:
            if result.intent in ["price_inquiry", "product_inquiry"]:
                result.intent = "price_objection"
                result.confidence = min(result.confidence * 1.3, 1.0)
                result.context_enhanced = True
                logger.debug("Pattern detected: Repeated price mentions → price_objection")

        # Multiple positive signals + closing stage → Final confirmation
        current_stage = fsm_state.get("current_stage")
        if patterns["positive_signals"] >= 2 and current_stage == "closing":
            if result.intent in ["positive_feedback", "unclear"]:
                result.intent = "final_confirmation"
                result.confidence = min(result.confidence * 1.2, 1.0)
                result.stage_suggestion = "closing"
                result.context_enhanced = True
                logger.debug("Pattern detected: Multiple positives in closing → final_confirmation")

        # Persistent hesitation → Soft rejection
        if patterns["hesitation_signals"] >= 3:
            if result.intent == "hesitation":
                result.intent = "soft_rejection"
                result.confidence = min(result.confidence * 1.1, 1.0)
                result.context_enhanced = True
                logger.debug("Pattern detected: Persistent hesitation → soft_rejection")

        return result

    def _calibrate_with_fsm_state(
        self,
        result: IntentResult,
        fsm_state: Dict[str, Any]
    ) -> IntentResult:
        """Calibrate intent based on current FSM stage"""

        current_stage = fsm_state.get("current_stage")

        # In opening stage, most questions are product_inquiry
        if current_stage == "opening":
            if result.intent in ["unclear", "filler"]:
                result.intent = "product_inquiry"
                result.stage_suggestion = "discovery"
                result.context_enhanced = True

        # In closing stage, price questions are likely final confirmations
        if current_stage == "closing":
            if result.intent in ["price_inquiry", "benefit_inquiry"]:
                result.intent = "final_confirmation"
                result.stage_suggestion = "closing"
                result.confidence = min(result.confidence * 1.2, 1.0)
                result.context_enhanced = True

        # In objection_handling, hesitation might be negotiation
        if current_stage == "objection_handling":
            if result.intent == "hesitation":
                result.intent = "negotiation"
                result.confidence = min(result.confidence * 1.1, 1.0)
                result.context_enhanced = True

        return result

    def _adjust_for_turn_count(
        self,
        result: IntentResult,
        turn_count: int
    ) -> IntentResult:
        """Adjust classification based on conversation length"""

        # Late in conversation (>10 turns)
        if turn_count > 10:
            # Greetings don't make sense late in conversation
            if result.intent == "greeting":
                result.intent = "filler"
                result.confidence *= 0.5
                result.context_enhanced = True

            # Hesitation late in conversation is likely soft rejection
            if result.intent == "hesitation":
                result.intent = "soft_rejection"
                result.confidence = min(result.confidence * 1.1, 1.0)
                result.context_enhanced = True

        # Very early in conversation (<=2 turns)
        if turn_count <= 2:
            # Most things are product inquiries or greetings
            if result.intent == "unclear":
                result.intent = "product_inquiry"
                result.confidence = 0.6
                result.context_enhanced = True

        return result
