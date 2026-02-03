from typing import Any, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailTool:
    """
    Mock Email Tool for AI SDR.
    Allows the agent to send outreach emails or follow-ups.
    """
    name = "outreach.send_email"
    
    def run(self, recipient: str, subject: str, body: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends an email to a lead.
        
        Args:
            recipient: Email address of the lead
            subject: Email subject line
            body: Email body content (HTML/Text)
            context: Optional context (e.g. session_id)
            
        Returns:
            Dict with status and message_id
        """
        # In a real system, this would connect to Gmail/Outlook API or SendGrid
        logger.info(f"📧 [AI SDR] Sending Email to {recipient}")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Body Preview: {body[:50]}...")
        
        # Simulate network latency or processing
        message_id = f"msg_{int(datetime.utcnow().timestamp())}"
        
        return {
            "status": "sent",
            "message_id": message_id,
            "timestamp": datetime.utcnow().isoformat(),
            "provider": "mock_smtp"
        }


from pydantic import Field
from app.tools.base import BaseTool, ToolInputModel


class EmailToolInput(ToolInputModel):
    recipient: str = Field(..., min_length=3, description="Recipient email")
    subject: str = Field(..., min_length=1, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional context")


class EmailToolWrapper(BaseTool):
    name = "outreach.send_email"
    description = "Send an outreach email to a lead."
    args_schema = EmailToolInput
    allowed_agents = {"sdr", "system"}

    def __init__(self) -> None:
        self._email = EmailTool()
        super().__init__()

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._email.run(
            recipient=payload["recipient"],
            subject=payload["subject"],
            body=payload["body"],
            context=payload.get("context"),
        )
