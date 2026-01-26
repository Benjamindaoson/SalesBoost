"""
Sentiment Analysis Service
Provides real-time sentiment detection for sales conversations.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SentimentService:
    """
    Analyzes user sentiment (Positive, Negative, Neutral, Anxious, Impatient).
    """
    
    def __init__(self):
        # In production, load a BERT model or call LLM
        # Here we use keyword heuristics for MVP speed
        self.keywords = {
            "negative": ["不需要", "太贵", "骗子", "滚", "别烦我", "垃圾", "no", "hate"],
            "positive": ["不错", "可以", "好的", "有趣", "继续", "yes", "great"],
            "anxious": ["担心", "风险", "安全吗", "怕", "worry", "考虑", "再看", "hesitate"],
            "impatient": ["快点", "啰嗦", "别废话", "hurry"]
        }

    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        Returns: {score: float, label: str, urgency: float}
        """
        text_lower = text.lower()
        
        # Simple keyword matching
        scores = {k: 0 for k in self.keywords}
        
        for label, words in self.keywords.items():
            for word in words:
                if word in text_lower:
                    scores[label] += 1
        
        # Determine dominant sentiment
        # Default
        label = "neutral"
        score = 0.5
        urgency = 0.0
        
        if scores["negative"] > 0:
            label = "negative"
            score = 0.1
            urgency = 0.8
        elif scores["impatient"] > 0:
            label = "impatient"
            score = 0.3
            urgency = 0.9
        elif scores["anxious"] > 0:
            label = "anxious"
            score = 0.4
            urgency = 0.6
        elif scores["positive"] > 0:
            label = "positive"
            score = 0.9
            urgency = 0.2
            
        return {
            "label": label,
            "score": score, # 0-1, 1 is positive
            "urgency": urgency # 0-1, 1 is high urgency
        }

# Global Instance
sentiment_service = SentimentService()
