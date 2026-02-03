"""
SMS Outreach Tool

Sends SMS messages for sales outreach and follow-ups.
Simulates integration with SMS providers like Twilio, MessageBird, etc.
"""
from typing import Dict, Any, Optional, List
from pydantic import Field
from datetime import datetime
import uuid

from app.tools.base import BaseTool, ToolInputModel
from app.infra.gateway.schemas import AgentType


class SMSOutreachInput(ToolInputModel):
    """SMS outreach input"""
    phone_number: str = Field(..., description="Recipient phone number (E.164 format)")
    message: str = Field(..., min_length=1, max_length=160, description="SMS message content (max 160 chars)")
    customer_id: Optional[str] = Field(None, description="Customer ID for tracking")
    campaign: Optional[str] = Field(None, description="Campaign name for analytics")


class SMSOutreachTool(BaseTool):
    """
    SMS Outreach Tool

    Sends SMS messages for sales outreach, follow-ups, and notifications.
    Features:
    - Send SMS to customers
    - Track delivery status
    - Campaign tracking
    - Message history

    Allowed agents: Coach, System
    """

    name = "sms_outreach"
    description = "Send SMS messages for sales outreach and follow-ups. Useful for quick customer engagement and reminders."
    args_schema = SMSOutreachInput
    allowed_agents = {
        AgentType.COACH.value,
        "system"
    }

    def __init__(self):
        super().__init__()
        # Simulated SMS history
        self._sms_history: List[Dict[str, Any]] = []
        # Rate limiting: track sends per phone number
        self._send_count: Dict[str, int] = {}

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send SMS message

        Args:
            payload: {
                "phone_number": "+1-555-0100",
                "message": "Hi John, following up on our conversation...",
                "customer_id": "CUST001",
                "campaign": "Q1_followup"
            }

        Returns:
            {
                "success": True,
                "message_id": "sms_abc123",
                "status": "sent",
                "phone_number": "+1-555-0100",
                "message_length": 45,
                "timestamp": "2026-01-30T10:30:00Z"
            }
        """
        phone_number = payload["phone_number"]
        message = payload["message"]
        customer_id = payload.get("customer_id")
        campaign = payload.get("campaign")

        # Validate phone number format
        if not self._validate_phone_number(phone_number):
            return {
                "success": False,
                "error": "Invalid phone number format. Use E.164 format (e.g., +1-555-0100)",
                "phone_number": phone_number
            }

        # Check rate limiting (max 5 SMS per phone per day)
        if self._check_rate_limit(phone_number):
            return {
                "success": False,
                "error": "Rate limit exceeded. Maximum 5 SMS per phone number per day.",
                "phone_number": phone_number,
                "current_count": self._send_count.get(phone_number, 0)
            }

        # Validate message length
        if len(message) > 160:
            return {
                "success": False,
                "error": f"Message too long. Maximum 160 characters, got {len(message)}",
                "message_length": len(message)
            }

        # Generate message ID
        message_id = f"sms_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Simulate sending SMS
        sms_record = {
            "message_id": message_id,
            "phone_number": phone_number,
            "message": message,
            "customer_id": customer_id,
            "campaign": campaign,
            "status": "sent",
            "timestamp": timestamp,
            "message_length": len(message),
            "segments": self._calculate_segments(message)
        }

        # Store in history
        self._sms_history.append(sms_record)

        # Update rate limit counter
        self._send_count[phone_number] = self._send_count.get(phone_number, 0) + 1

        return {
            "success": True,
            "message_id": message_id,
            "status": "sent",
            "phone_number": phone_number,
            "message_length": len(message),
            "segments": sms_record["segments"],
            "timestamp": timestamp,
            "customer_id": customer_id,
            "campaign": campaign,
            "delivery_estimate": "1-5 seconds"
        }

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format (basic E.164 check)"""
        # Remove common separators
        cleaned = phone_number.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

        # Check if starts with + and has 10-15 digits
        if cleaned.startswith("+"):
            digits = cleaned[1:]
            return digits.isdigit() and len(digits) >= 10 and len(digits) <= 15

        return False

    def _check_rate_limit(self, phone_number: str) -> bool:
        """Check if rate limit exceeded"""
        current_count = self._send_count.get(phone_number, 0)
        return current_count >= 5

    def _calculate_segments(self, message: str) -> int:
        """Calculate number of SMS segments"""
        # Standard SMS: 160 chars per segment
        # With special chars: 70 chars per segment
        has_special = any(ord(c) > 127 for c in message)
        segment_size = 70 if has_special else 160

        return (len(message) + segment_size - 1) // segment_size

    async def get_history(self, phone_number: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Get SMS history"""
        if phone_number:
            history = [sms for sms in self._sms_history if sms["phone_number"] == phone_number]
        else:
            history = self._sms_history

        return {
            "success": True,
            "count": len(history),
            "history": history[-limit:]
        }

    async def get_campaign_stats(self, campaign: str) -> Dict[str, Any]:
        """Get campaign statistics"""
        campaign_sms = [sms for sms in self._sms_history if sms.get("campaign") == campaign]

        return {
            "success": True,
            "campaign": campaign,
            "total_sent": len(campaign_sms),
            "unique_recipients": len(set(sms["phone_number"] for sms in campaign_sms)),
            "total_segments": sum(sms["segments"] for sms in campaign_sms)
        }
