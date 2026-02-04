"""
A2A-enabled Coach Agent

Sales coaching agent with A2A communication capabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.a2a.agent_base import A2AAgent
from app.a2a.message_bus import A2AMessageBus
from app.a2a.protocol import A2AMessage

logger = logging.getLogger(__name__)


class CoachAgentA2A(A2AAgent):
    """
    A2A-enabled Coach Agent

    Provides real-time coaching and feedback to sales agents.

    Capabilities:
    - coaching: Provide sales coaching
    - feedback: Give feedback on performance
    - evaluation: Evaluate sales interactions
    - suggestion: Suggest improvements
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: A2AMessageBus,
        llm_client: Optional[Any] = None,
        **kwargs,
    ):
        """
        Initialize Coach Agent

        Args:
            agent_id: Unique agent identifier
            message_bus: Message bus instance
            llm_client: LLM client for generating feedback
            **kwargs: Additional arguments
        """
        super().__init__(
            agent_id=agent_id,
            message_bus=message_bus,
            capabilities=["coaching", "feedback", "evaluation", "suggestion"],
            agent_type="CoachAgent",
            metadata={"version": "2.0", "a2a_enabled": True},
            **kwargs,
        )

        self.llm_client = llm_client

        # Coaching history
        self.coaching_history: Dict[str, list] = {}

    async def handle_request(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming requests

        Supported actions:
        - get_suggestion: Get coaching suggestion
        - evaluate_response: Evaluate a sales response
        - provide_feedback: Provide detailed feedback
        - analyze_conversation: Analyze entire conversation
        """
        action = message.payload.get("action")
        parameters = message.payload.get("parameters", {})

        if action == "get_suggestion":
            return await self._get_suggestion(parameters)
        elif action == "evaluate_response":
            return await self._evaluate_response(parameters)
        elif action == "provide_feedback":
            return await self._provide_feedback(parameters)
        elif action == "analyze_conversation":
            return await self._analyze_conversation(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def handle_event(self, message: A2AMessage):
        """Handle incoming events"""
        event_type = message.payload.get("event_type")
        data = message.payload.get("data", {})

        if event_type == "response_generated":
            # SDR generated a response - provide proactive feedback
            await self._provide_proactive_feedback(message.from_agent, data)
        elif event_type == "deal_closed":
            # Deal closed - analyze and provide insights
            await self._analyze_deal_closure(message.from_agent, data)
        elif event_type == "lead_qualified":
            # Lead qualified - provide feedback on qualification
            await self._feedback_on_qualification(message.from_agent, data)
        else:
            logger.debug(f"Coach Agent received event: {event_type}")

    async def _get_suggestion(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get coaching suggestion

        Args:
            parameters: {
                "customer_message": str,
                "context": dict,
                "stage": str
            }

        Returns:
            Coaching suggestion
        """
        customer_message = parameters.get("customer_message")
        context = parameters.get("context", {})
        stage = parameters.get("stage", "discovery")

        logger.info(f"Providing suggestion for stage: {stage}")

        # Analyze the situation
        suggestion = {
            "recommended_approach": self._get_approach_for_stage(stage),
            "key_points": [
                "Focus on understanding customer needs",
                "Ask open-ended questions",
                "Listen actively",
            ],
            "avoid": ["Being too pushy", "Talking too much about features"],
            "confidence": 0.9,
        }

        return suggestion

    async def _evaluate_response(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a sales response

        Args:
            parameters: {
                "response": str,
                "customer_message": str,
                "context": dict
            }

        Returns:
            Evaluation result
        """
        response = parameters.get("response")
        customer_message = parameters.get("customer_message")

        logger.info("Evaluating sales response")

        evaluation = {
            "overall_score": 8.5,
            "strengths": [
                "Good empathy",
                "Clear communication",
                "Addressed customer concern",
            ],
            "weaknesses": ["Could ask more questions", "Missed opportunity to upsell"],
            "improvement_suggestions": [
                "Try to understand the root cause of the objection",
                "Use more open-ended questions",
            ],
            "tone_analysis": {"empathy": 0.9, "confidence": 0.8, "professionalism": 0.95},
        }

        return evaluation

    async def _provide_feedback(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide detailed feedback

        Args:
            parameters: {
                "conversation_history": list,
                "metrics": dict
            }

        Returns:
            Detailed feedback
        """
        conversation_history = parameters.get("conversation_history", [])
        metrics = parameters.get("metrics", {})

        logger.info("Providing detailed feedback")

        feedback = {
            "overall_performance": "Good",
            "score": 8.0,
            "strengths": [
                "Excellent rapport building",
                "Good objection handling",
                "Clear value proposition",
            ],
            "areas_for_improvement": [
                "Discovery questions could be deeper",
                "Closing could be more confident",
            ],
            "specific_recommendations": [
                {
                    "area": "Discovery",
                    "recommendation": "Use SPIN selling technique",
                    "example": "Ask more situation and problem questions",
                },
                {
                    "area": "Closing",
                    "recommendation": "Use assumptive close",
                    "example": "When would you like to get started?",
                },
            ],
            "next_training_focus": ["Advanced closing techniques", "Handling price objections"],
        }

        return feedback

    async def _analyze_conversation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze entire conversation

        Args:
            parameters: {
                "conversation_id": str,
                "messages": list
            }

        Returns:
            Conversation analysis
        """
        conversation_id = parameters.get("conversation_id")
        messages = parameters.get("messages", [])

        logger.info(f"Analyzing conversation: {conversation_id}")

        analysis = {
            "conversation_id": conversation_id,
            "total_messages": len(messages),
            "stages_covered": ["Opening", "Discovery", "Pitch", "Objection Handling"],
            "effectiveness_score": 8.2,
            "key_moments": [
                {
                    "timestamp": "00:05:30",
                    "type": "breakthrough",
                    "description": "Customer revealed budget",
                },
                {
                    "timestamp": "00:12:15",
                    "type": "challenge",
                    "description": "Price objection",
                },
            ],
            "outcome": "Qualified lead",
            "recommendations": [
                "Follow up within 24 hours",
                "Send case study on ROI",
                "Schedule demo for next week",
            ],
        }

        return analysis

    def _get_approach_for_stage(self, stage: str) -> str:
        """Get recommended approach for sales stage"""
        approaches = {
            "opening": "Build rapport and establish credibility",
            "discovery": "Ask open-ended questions to understand needs",
            "pitch": "Present solution aligned with discovered needs",
            "objection_handling": "Acknowledge, reframe, and provide evidence",
            "closing": "Use assumptive close or alternative choice",
        }
        return approaches.get(stage, "Focus on customer needs")

    async def _provide_proactive_feedback(self, agent_id: str, data: Dict[str, Any]):
        """Provide proactive feedback when SDR generates response"""
        response = data.get("response", {})
        stage = data.get("stage")

        logger.info(f"Providing proactive feedback to {agent_id} for stage {stage}")

        # Send feedback event
        await self.send_event(
            to_agent=agent_id,
            event_type="coach_feedback",
            data={
                "feedback": f"Good response for {stage} stage",
                "score": response.get("confidence", 0.8),
                "tips": ["Keep the momentum going", "Ask for commitment"],
            },
        )

    async def _analyze_deal_closure(self, agent_id: str, data: Dict[str, Any]):
        """Analyze deal closure and provide insights"""
        deal_info = data.get("deal_info", {})
        result = data.get("result", {})

        logger.info(f"Analyzing deal closure for {agent_id}")

        # Send analysis event
        await self.send_event(
            to_agent=agent_id,
            event_type="deal_analysis",
            data={
                "congratulations": True,
                "deal_value": result.get("deal_value", 0),
                "key_success_factors": [
                    "Strong discovery",
                    "Clear value proposition",
                    "Effective objection handling",
                ],
                "lessons_learned": ["Technique worked well", "Customer was well-qualified"],
            },
        )

    async def _feedback_on_qualification(self, agent_id: str, data: Dict[str, Any]):
        """Provide feedback on lead qualification"""
        qualification = data.get("qualification", {})

        logger.info(f"Providing qualification feedback to {agent_id}")

        await self.send_event(
            to_agent=agent_id,
            event_type="qualification_feedback",
            data={
                "score": qualification.get("score", 0),
                "feedback": "Good qualification process",
                "suggestions": ["Verify budget authority", "Confirm timeline"],
            },
        )
