"""
A2A-enabled SDR Agent

Sales Development Representative agent with A2A communication capabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.a2a.agent_base import A2AAgent
from app.a2a.message_bus import A2AMessageBus
from app.a2a.protocol import A2AMessage

logger = logging.getLogger(__name__)


class SDRAgentA2A(A2AAgent):
    """
    A2A-enabled SDR Agent

    Sales Development Representative agent that can:
    - Communicate with Coach Agent for feedback
    - Communicate with Compliance Agent for checks
    - Broadcast sales events
    - Query knowledge base agent

    Capabilities:
    - sales: Handle sales conversations
    - objection_handling: Handle customer objections
    - closing: Close deals
    - lead_qualification: Qualify leads
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: A2AMessageBus,
        llm_client: Optional[Any] = None,
        tool_executor: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initialize SDR Agent

        Args:
            agent_id: Unique agent identifier
            message_bus: Message bus instance
            llm_client: LLM client for generating responses
            tool_executor: Tool executor for using tools
            **kwargs: Additional arguments
        """
        super().__init__(
            agent_id=agent_id,
            message_bus=message_bus,
            capabilities=[
                "sales",
                "objection_handling",
                "closing",
                "lead_qualification",
            ],
            agent_type="SDRAgent",
            metadata={"version": "2.0", "a2a_enabled": True},
            **kwargs,
        )

        self.llm_client = llm_client
        self.tool_executor = tool_executor

        # Conversation state
        self.conversation_state: Dict[str, Any] = {}

    async def handle_request(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming requests

        Supported actions:
        - generate_response: Generate sales response
        - handle_objection: Handle customer objection
        - qualify_lead: Qualify a lead
        - close_deal: Attempt to close deal
        """
        action = message.payload.get("action")
        parameters = message.payload.get("parameters", {})

        if action == "generate_response":
            return await self._generate_response(parameters)
        elif action == "handle_objection":
            return await self._handle_objection(parameters)
        elif action == "qualify_lead":
            return await self._qualify_lead(parameters)
        elif action == "close_deal":
            return await self._close_deal(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def handle_event(self, message: A2AMessage):
        """Handle incoming events"""
        event_type = message.payload.get("event_type")
        data = message.payload.get("data", {})

        if event_type == "customer_message":
            # Customer sent a message
            await self._process_customer_message(data)
        elif event_type == "coach_feedback":
            # Received feedback from coach
            await self._process_coach_feedback(data)
        elif event_type == "compliance_alert":
            # Compliance issue detected
            await self._handle_compliance_alert(data)
        else:
            logger.debug(f"SDR Agent received event: {event_type}")

    async def _generate_response(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate sales response

        Args:
            parameters: {
                "customer_message": str,
                "context": dict,
                "stage": str
            }

        Returns:
            Generated response
        """
        customer_message = parameters.get("customer_message")
        context = parameters.get("context", {})
        stage = parameters.get("stage", "discovery")

        logger.info(f"Generating response for stage: {stage}")

        # Request coach feedback before responding
        coach_agents = await self.discover_agents(capability="coaching")
        if coach_agents:
            try:
                feedback_response = await self.send_request(
                    to_agent=coach_agents[0],
                    action="get_suggestion",
                    parameters={
                        "customer_message": customer_message,
                        "context": context,
                        "stage": stage,
                    },
                    timeout=5.0,
                )
                coach_suggestion = feedback_response.payload.get("result", {})
                logger.info(f"Received coach suggestion: {coach_suggestion}")
            except Exception as e:
                logger.warning(f"Could not get coach feedback: {e}")
                coach_suggestion = {}
        else:
            coach_suggestion = {}

        # Generate response (simplified - would use LLM in production)
        response = {
            "message": f"Thank you for your message. Let me help you with that.",
            "stage": stage,
            "coach_suggestion": coach_suggestion,
            "confidence": 0.85,
        }

        # Broadcast event
        await self.broadcast_event(
            event_type="response_generated",
            data={"response": response, "stage": stage},
        )

        return response

    async def _handle_objection(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle customer objection

        Args:
            parameters: {
                "objection": str,
                "objection_type": str,
                "context": dict
            }

        Returns:
            Objection handling response
        """
        objection = parameters.get("objection")
        objection_type = parameters.get("objection_type", "unknown")

        logger.info(f"Handling objection type: {objection_type}")

        # Request knowledge from knowledge agent
        knowledge_agents = await self.discover_agents(capability="knowledge")
        if knowledge_agents:
            try:
                knowledge_response = await self.send_query(
                    to_agent=knowledge_agents[0],
                    query=f"objection handling {objection_type}",
                    filters={"category": "objections"},
                    limit=3,
                    timeout=5.0,
                )
                knowledge = knowledge_response.payload.get("result", {})
            except Exception as e:
                logger.warning(f"Could not get knowledge: {e}")
                knowledge = {}
        else:
            knowledge = {}

        response = {
            "objection_response": f"I understand your concern about {objection_type}.",
            "objection_type": objection_type,
            "knowledge_used": knowledge,
            "success": True,
        }

        return response

    async def _qualify_lead(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Qualify a lead

        Args:
            parameters: {
                "lead_info": dict,
                "conversation_history": list
            }

        Returns:
            Lead qualification result
        """
        lead_info = parameters.get("lead_info", {})

        logger.info(f"Qualifying lead: {lead_info.get('name', 'unknown')}")

        qualification = {
            "qualified": True,
            "score": 75,
            "reasons": ["Budget confirmed", "Decision maker identified"],
            "next_steps": ["Schedule demo", "Send proposal"],
        }

        # Broadcast qualification event
        await self.broadcast_event(
            event_type="lead_qualified", data={"lead_info": lead_info, "qualification": qualification}
        )

        return qualification

    async def _close_deal(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to close deal

        Args:
            parameters: {
                "deal_info": dict,
                "closing_technique": str
            }

        Returns:
            Closing attempt result
        """
        deal_info = parameters.get("deal_info", {})
        technique = parameters.get("closing_technique", "assumptive")

        logger.info(f"Attempting to close deal using {technique} technique")

        # Check compliance before closing
        compliance_agents = await self.discover_agents(capability="compliance_check")
        if compliance_agents:
            try:
                compliance_response = await self.send_request(
                    to_agent=compliance_agents[0],
                    action="check_compliance",
                    parameters={"deal_info": deal_info},
                    timeout=5.0,
                )
                compliance_result = compliance_response.payload.get("result", {})
                if not compliance_result.get("compliant", True):
                    return {
                        "success": False,
                        "reason": "Compliance check failed",
                        "violations": compliance_result.get("violations", []),
                    }
            except Exception as e:
                logger.warning(f"Could not check compliance: {e}")

        result = {
            "success": True,
            "deal_value": deal_info.get("value", 0),
            "technique_used": technique,
            "next_steps": ["Send contract", "Schedule onboarding"],
        }

        # Broadcast deal closed event
        await self.broadcast_event(
            event_type="deal_closed", data={"deal_info": deal_info, "result": result}
        )

        return result

    async def _process_customer_message(self, data: Dict[str, Any]):
        """Process customer message event"""
        message = data.get("message")
        logger.info(f"Processing customer message: {message[:50]}...")

    async def _process_coach_feedback(self, data: Dict[str, Any]):
        """Process coach feedback event"""
        feedback = data.get("feedback")
        logger.info(f"Received coach feedback: {feedback}")

    async def _handle_compliance_alert(self, data: Dict[str, Any]):
        """Handle compliance alert"""
        alert = data.get("alert")
        logger.warning(f"Compliance alert: {alert}")
