import logging
import uuid
from typing import Any, Dict
from datetime import datetime

from app.agents.roles.base import BaseAgent
from app.schemas.blackboard import BlackboardSchema, PendingAction
from app.infra.gateway.schemas import AgentType

logger = logging.getLogger(__name__)

class SDRAgent(BaseAgent):
    """
    AI Sales Development Representative (SDR).
    Autonomous agent that acts as a salesperson to acquire leads.
    
    Capabilities:
    - Conversational Selling (via Chat/Voice)
    - Objection Handling
    - Tool Usage (Email, Calendar)
    - CRM Updates
    """
    
    def __init__(self, model_gateway=None):
        super().__init__()
        self.gateway = model_gateway
        self.system_prompt_template = """
You are Alex, a top-tier Sales Development Representative (SDR) at SalesBoost.
Your goal is to qualify leads and book meetings. You are NOT a simulator; you are a REAL employee.

Current Context:
- Lead Name: {lead_name}
- CRM Stage: {crm_stage}
- Last Intent: {last_intent}
- Psychology: Trust={trust}, Interest={interest}

Operational Rules:
1. Be professional, concise, and empathetic.
2. If the lead is interested, propose a meeting time.
3. If the lead asks for info, offer to send an email summary.
4. If the lead is busy, ask for a better time to follow up.

Output strictly JSON:
{
  "thought": "internal reasoning",
  "response_text": "what you say to the lead (or null if action only)",
  "action": {
      "type": "send_email | book_meeting | update_crm | none",
      "payload": { ... }
  }
}
"""

    async def generate_next_step(
        self, 
        user_message: str, 
        blackboard: BlackboardSchema
    ) -> Dict[str, Any]:
        """
        Decide the next move: Speak or Act.
        """
        logger.info(f"🤖 [SDR Agent] Thinking about: {user_message[:50]}...")
        
        # 1. Prepare Context
        lead_name = blackboard.external_context.participants[0] if blackboard.external_context.participants else "Valued Lead"
        crm_stage = blackboard.external_context.crm_stage_mapped or "New Lead"
        
        self.system_prompt_template.format(
            lead_name=lead_name,
            crm_stage=crm_stage,
            last_intent=blackboard.last_intent or "unknown",
            trust=blackboard.psychology.trust,
            interest=blackboard.psychology.interest
        )
        
        # 2. Call LLM
        if not self.gateway:
            # Mock fallback for demo
            return {
                "thought": "Gateway missing, using fallback",
                "response_text": "I'd love to tell you more about SalesBoost. Can we schedule a quick call?",
                "action": {"type": "none", "payload": {}}
            }

        # Real LLM Call logic would go here (similar to NPCGenerator)
        # For this prototype, I'll simulate a "Smart" response based on keywords
        
        # ... (Gateway call implementation omitted for brevity, assuming standard pattern) ...
        
        # Simulated "Brain" Logic for Demo:
        action_type = "none"
        payload = {}
        response_text = ""
        
        msg_lower = user_message.lower()
        
        if "send me info" in msg_lower or "email" in msg_lower:
            action_type = "send_email"
            payload = {
                "recipient": "lead@example.com", # In real app, get from context
                "subject": "SalesBoost Overview",
                "body": "Here is the information you requested..."
            }
            response_text = "I've sent that email over to you just now. Is there anything specific you'd like to discuss?"
            
        elif "book" in msg_lower or "meet" in msg_lower or "schedule" in msg_lower:
            action_type = "book_meeting"
            payload = {"time": "tomorrow 10am"}
            response_text = "Great! I'll send a calendar invite for tomorrow at 10am."
            
        else:
            # Default conversation
            response_text = "That makes sense. Could you share what your biggest challenge is with your current sales training?"
            
        return {
            "thought": f"User said '{user_message}', detected intent related to {action_type}",
            "response_text": response_text,
            "action": {
                "type": action_type,
                "payload": payload
            }
        }

    async def execute_action(self, action: Dict[str, Any], blackboard: BlackboardSchema) -> None:
        """
        Execute the decided action and update Blackboard.
        """
        act_type = action.get("type")
        payload = action.get("payload")
        
        if act_type == "none":
            return
            
        logger.info(f"⚡ [SDR Agent] Executing Action: {act_type}")
        
        # Create a PendingAction in Blackboard
        new_action = PendingAction(
            action_type=act_type,
            payload=payload,
            status="pending",
            created_at=datetime.utcnow()
        )
        blackboard.pending_actions.append(new_action)
        
        # In a real "Autonomous" mode, we might execute it immediately via ToolExecutor
        if act_type == "send_email":
            from app.tools.executor import ToolExecutor
            from app.tools.registry import ToolRegistry
            from app.tools.outreach.email_tool import EmailToolWrapper

            registry = ToolRegistry()
            registry.register(EmailToolWrapper())
            executor = ToolExecutor(registry)

            exec_result = await executor.execute(
                "outreach.send_email",
                {
                    "recipient": payload.get("recipient", "unknown"),
                    "subject": payload.get("subject", "No Subject"),
                    "body": payload.get("body", ""),
                },
                caller_role=AgentType.SDR.value,
                tool_call_id=f"sdr-{uuid.uuid4().hex}",
            )
            new_action.status = "executed" if exec_result["ok"] else "failed"
