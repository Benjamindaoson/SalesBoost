import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("alerting")

class AlertManager:
    """
    Simple Alert Manager for business metrics.
    Intended to be connected to PagerDuty or Slack in production.
    """
    
    def __init__(self):
        self.logger = logger

    async def check_business_metrics(self, metrics: Dict[str, Any]):
        """
        Check business metrics against thresholds and trigger alerts.
        """
        # 1. Sentiment Alert
        sentiment = metrics.get("sentiment_score")
        if sentiment is not None and sentiment < 0.3:
            self.trigger_alert(
                "CRITICAL_SENTIMENT_DROP", 
                f"User sentiment dropped to {sentiment}. Potential churn risk.",
                severity="high"
            )
            
        # 2. Refusal/Failure Rate
        refusal_rate = metrics.get("refusal_rate", 0)
        if refusal_rate > 0.15:
             self.trigger_alert(
                "HIGH_REFUSAL_RATE",
                f"Refusal rate is {refusal_rate*100}%. Check RAG knowledge base.",
                severity="medium"
            )

    def trigger_alert(self, alert_type: str, message: str, severity: str = "info"):
        # In MVP, we just log as WARNING/ERROR
        if severity == "high":
            self.logger.error(f"[ALERT][{alert_type}] {message}")
        else:
            self.logger.warning(f"[ALERT][{alert_type}] {message}")

alert_manager = AlertManager()
