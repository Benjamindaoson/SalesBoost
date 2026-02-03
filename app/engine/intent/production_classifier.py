"""
Production Intent Classifier using FastText

This module provides a production-ready intent classification system
combining FastText ML model with rule-based fallbacks.
"""
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from collections import Counter

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    logging.warning("FastText not available, falling back to rule-based classification")

from app.engine.intent.schemas import IntentResult, SalesStage

logger = logging.getLogger(__name__)


class ProductionIntentClassifier:
    """
    Production-Ready Intent Classifier

    Features:
    - FastText ML model for accurate classification
    - Rule-based fallback for robustness
    - Chinese and English support
    - Context-aware adjustments
    """

    def __init__(self, model_path: str = "models/intent_classifier.bin"):
        """
        Initialize the classifier

        Args:
            model_path: Path to the FastText model file
        """
        self.model_path = Path(model_path)
        self.model = None
        self.confidence_threshold = 0.7
        self.prediction_counter = Counter()

        # Intent to sales stage mapping
        self.intent_to_stage = {
            "price_objection": SalesStage.OBJECTION_HANDLING,
            "price_inquiry": SalesStage.DISCOVERY,
            "product_inquiry": SalesStage.DISCOVERY,
            "benefit_inquiry": SalesStage.DISCOVERY,
            "positive_feedback": SalesStage.CLOSING,
            "hesitation": SalesStage.OBJECTION_HANDLING,
            "negotiation": SalesStage.OBJECTION_HANDLING,
            "time_pressure": SalesStage.OBJECTION_HANDLING,
            "case_request": SalesStage.PRESENTATION,
            "competitor_comparison": SalesStage.OBJECTION_HANDLING,
            "final_confirmation": SalesStage.CLOSING,
            "soft_rejection": SalesStage.OBJECTION_HANDLING,
        }

        # Load FastText model if available
        if FASTTEXT_AVAILABLE and self.model_path.exists():
            try:
                self.model = fasttext.load_model(str(self.model_path))
                logger.info(f"Loaded FastText model from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load FastText model: {e}")
                self.model = None
        else:
            if not FASTTEXT_AVAILABLE:
                logger.warning("FastText not installed, using rule-based fallback")
            elif not self.model_path.exists():
                logger.warning(f"Model file not found: {self.model_path}, using rule-based fallback")

    async def classify(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> IntentResult:
        """
        Classify user message intent

        Args:
            message: User input text
            context: Context dictionary with current_stage, etc.

        Returns:
            IntentResult with intent, confidence, and stage suggestion
        """
        start_time = time.time()

        # Preprocess
        cleaned_msg = self._preprocess(message)

        # Try FastText model first
        if self.model:
            try:
                result = self._classify_with_fasttext(cleaned_msg)
            except Exception as e:
                logger.error(f"FastText classification failed: {e}, falling back to rules")
                result = self._classify_with_rules(cleaned_msg)
        else:
            # Fallback to rule-based
            result = self._classify_with_rules(cleaned_msg)

        # Context enhancement
        result = self._enhance_with_context(result, context)

        # Track metrics
        latency_ms = (time.time() - start_time) * 1000
        self.prediction_counter[result.intent] += 1

        logger.debug(f"Intent classified as '{result.intent}' with confidence {result.confidence:.3f} in {latency_ms:.1f}ms")

        return result

    def _classify_with_fasttext(self, text: str) -> IntentResult:
        """Classify using FastText model"""
        import numpy as np
        import warnings

        # Suppress numpy copy warnings from FastText
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)

            # Predict with k=3 to get top 3 candidates
            predictions = self.model.predict(text, k=3)

            # Handle both old and new fasttext return formats
            if isinstance(predictions, tuple) and len(predictions) == 2:
                labels, probabilities = predictions
            else:
                labels = predictions[0] if hasattr(predictions, '__getitem__') else [predictions]
                probabilities = [1.0]

            # Convert to numpy arrays safely (numpy 2.x compatible)
            labels = np.asarray(labels) if not isinstance(labels, (list, tuple)) else labels
            probabilities = np.asarray(probabilities) if not isinstance(probabilities, (list, tuple)) else probabilities

        # Extract primary intent
        primary_label = str(labels[0]).replace("__label__", "")
        primary_confidence = float(probabilities[0])

        # Extract alternative intents
        alternative_intents = []
        for i in range(1, min(3, len(labels))):
            alt_label = str(labels[i]).replace("__label__", "")
            alt_confidence = float(probabilities[i])
            alternative_intents.append({
                "intent": alt_label,
                "confidence": alt_confidence
            })

        # Get stage suggestion
        stage_suggestion = self.intent_to_stage.get(primary_label)

        return IntentResult(
            intent=primary_label,
            confidence=primary_confidence,
            stage_suggestion=stage_suggestion.value if stage_suggestion else None,
            alternative_intents=alternative_intents,
            context_enhanced=False,
            model_version="fasttext_v1.0"
        )

    def _classify_with_rules(self, text: str) -> IntentResult:
        """Fallback rule-based classification"""
        text_lower = text.lower()

        # Price objection patterns
        if any(pattern in text_lower for pattern in [
            "太贵", "贵了", "expensive", "too much", "价格", "便宜", "discount", "折扣"
        ]):
            return IntentResult(
                intent="price_objection",
                confidence=0.8,
                stage_suggestion=SalesStage.OBJECTION_HANDLING.value,
                model_version="rules_v1.0"
            )

        # Product inquiry patterns
        if any(pattern in text_lower for pattern in [
            "功能", "特色", "怎么", "如何", "feature", "how", "what is"
        ]):
            return IntentResult(
                intent="product_inquiry",
                confidence=0.75,
                stage_suggestion=SalesStage.DISCOVERY.value,
                model_version="rules_v1.0"
            )

        # Positive feedback
        if any(pattern in text_lower for pattern in [
            "不错", "好的", "可以", "感兴趣", "good", "great", "interested"
        ]):
            return IntentResult(
                intent="positive_feedback",
                confidence=0.7,
                stage_suggestion=SalesStage.CLOSING.value,
                model_version="rules_v1.0"
            )

        # Hesitation
        if any(pattern in text_lower for pattern in [
            "考虑", "想想", "犹豫", "think", "consider", "not sure"
        ]):
            return IntentResult(
                intent="hesitation",
                confidence=0.75,
                stage_suggestion=SalesStage.OBJECTION_HANDLING.value,
                model_version="rules_v1.0"
            )

        # Default: unclear
        return IntentResult(
            intent="unclear",
            confidence=0.5,
            stage_suggestion=None,
            model_version="rules_v1.0"
        )

    def _enhance_with_context(
        self,
        result: IntentResult,
        context: Dict[str, Any]
    ) -> IntentResult:
        """Enhance classification with context awareness"""
        current_stage = context.get("current_stage")

        # If in closing stage, upgrade price inquiries to final confirmation
        if current_stage == SalesStage.CLOSING.value:
            if result.intent in ["price_inquiry", "price_objection"]:
                result.intent = "final_confirmation"
                result.confidence = min(result.confidence * 1.2, 1.0)
                result.stage_suggestion = SalesStage.CLOSING.value
                result.context_enhanced = True

        # If late in conversation and hesitating, might be soft rejection
        turn_count = context.get("turn_count", 0)
        if turn_count > 10 and result.intent == "hesitation":
            result.intent = "soft_rejection"
            result.stage_suggestion = SalesStage.OBJECTION_HANDLING.value
            result.context_enhanced = True

        return result

    def _preprocess(self, text: str) -> str:
        """Preprocess text for classification"""
        # Remove special characters, keep Chinese, English, and numbers
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        text = text.lower().strip()
        return text

    def _is_chinese_text(self, text: str) -> bool:
        """Check if text is predominantly Chinese"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.replace(" ", ""))
        return chinese_chars / max(total_chars, 1) > 0.3

    def get_statistics(self) -> Dict[str, Any]:
        """Get classification statistics"""
        total = sum(self.prediction_counter.values())
        return {
            "total_predictions": total,
            "distribution": dict(self.prediction_counter),
            "model_loaded": self.model is not None,
            "model_path": str(self.model_path)
        }
